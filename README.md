# Gesture-Based Vocal Effects Control System

This project implements an interactive system that allows singers to control vocal effects in real time through hand gestures captured through the laptop camera.

## Main Features

- Real-time hand tracking using MediaPipe
- Gesture-based effect selection
- Right-hand modulation of vocal effect parameters
- MIDI Control Change messages sent to Logic Pro X
- Two interaction modes:
  - MOD_1: pinch-based modulation
  - MOD_2: hand openness-based modulation

## Project Structure

- `src/`: Python source code
- `docs/`: project documentation
- `assets/`: images and diagrams
- `tests/`: testing material

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
