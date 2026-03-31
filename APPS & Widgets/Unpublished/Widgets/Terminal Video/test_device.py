"""
Simple test script to verify device connectivity and API support.
"""
import asyncio
from busylib import AsyncBusyBar


async def test_device():
    """Test basic device connectivity."""
    addr = "10.0.4.20"
    
    print(f"Testing connection to {addr}...")
    
    async with AsyncBusyBar(addr) as client:
        print("\n✓ Connected successfully!")
        
        # Test version
        try:
            version = await client.get_version()
            print(f"\n✓ Version: {version.api_semver}")
        except Exception as e:
            print(f"\n✗ Version failed: {e}")
        
        # Test device name
        try:
            name = await client.get_device_name()
            print(f"✓ Device Name: {name.name}")
        except Exception as e:
            print(f"✗ Device Name failed: {e}")
        
        # Test status
        try:
            status = await client.get_status()
            if status.system:
                print(f"✓ System: {status.system.version} - Uptime: {status.system.uptime}")
            if status.power:
                print(f"✓ Battery: {status.power.battery_charge}% ({status.power.state})")
        except Exception as e:
            print(f"✗ Status failed: {e}")
        
        # Test screen capture via HTTP
        try:
            print("\n✓ Testing HTTP screen capture...")
            from busylib import display
            spec = display.get_display_spec(display.FRONT_DISPLAY)
            frame = await client.get_screen_frame(spec)
            print(f"✓ Got frame: {len(frame)} bytes")
        except Exception as e:
            print(f"✗ Screen capture failed: {e}")
        
        # Test WebSocket support
        print("\n✓ Testing WebSocket streaming support...")
        try:
            spec = display.get_display_spec(display.FRONT_DISPLAY)
            frame_count = 0
            async for message in client.stream_screen_ws(spec):
                frame_count += 1
                if isinstance(message, bytes):
                    print(f"✓ Got frame {frame_count}: {len(message)} bytes")
                else:
                    print(f"  Server message: {message}")
                
                if frame_count >= 3:
                    print("✓ WebSocket streaming works!")
                    break
        except Exception as e:
            print(f"✗ WebSocket streaming not supported: {e}")
            print("  → This device may need HTTP polling mode")


if __name__ == "__main__":
    asyncio.run(test_device())
