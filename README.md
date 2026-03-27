# BSB Custom Widgets (and AI Lessons)

This repo contains:

- **Widgets** (host-side scripts that `POST /api/display/draw` to the BUSY Bar)
- **On-device apps** (JerryScript / Lua / etc. depending on firmware)
- **AI lesson materials** for building BUSY Bar widgets/apps

## Start here (pick one)

- **I want to build a widget fast (recommended)**: start with **AI Lessons** → `BSB-AI Lessons/README.md` (then `BSB-AI Lessons/Official/README.md`)
- **I want ready-to-use widgets**: `Published/Widgets/`
- **I’m browsing experiments / WIP apps & widgets**: `APPS & Widgets/Unpublished/`

## Key docs

- **Changelog (canonical)**: `CHANGELOG.md`
- **BUSY Bar HTTP API spec** (from lessons): `BSB-AI Lessons/Official/openapi.yaml`

## Index (most important READMEs)

- **AI Lessons overview**: `BSB-AI Lessons/README.md`
- **AI Lessons (HTTP widgets path)**: `BSB-AI Lessons/Official/README.md`
- **Bus Timetables (JerryScript app)**: `APPS & Widgets/Unpublished/APPS/Bus Timetables/README.md`
- **Blackmagic Camera Control (web app)**: `APPS & Widgets/Unpublished/Widgets/Blackmagic Test/README.md`
- **Premiere Pro Timeline timecode (CEP/UXP + BUSY Bar)**: `APPS & Widgets/Unpublished/Widgets/Premiere Pro Timeline/README.md`
- **Resolve API export progress (BUSY Bar)**: `APPS & Widgets/Unpublished/Widgets/Resolve API/Resolve API/README.md`
- **Terminal Video**: `APPS & Widgets/Unpublished/Widgets/Terminal Video/README.md`

## Repo structure (high level)

- `Published/Widgets/`: things intended to be shareable/ready
- `APPS & Widgets/Unpublished/`: experiments and in-progress apps/widgets
- `BSB-AI Lessons/`: AI prompt + reference materials (now tracked in this repo)

## Where is…?

- **A “widget.py” you run on your computer**: usually under `Published/Widgets/` (ready) or `APPS & Widgets/Unpublished/Widgets/` (WIP)
- **An app that runs on the device**: usually under `APPS & Widgets/Unpublished/APPS/`
- **API reference / how to draw to the screen**: `BSB-AI Lessons/Official/openapi.yaml` + `BSB-AI Lessons/Official/03-Device-and-API.md`

