# Robot LLM Controller

This application provides a natural language interface to control the RobotGrid application using an OpenAI-compatible Large Language Model (LLM).

## Setup

1. Make sure the RobotGrid application is running
2. Create a Python virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Copy the example environment file and add your OpenAI API key:
   ```
   cp .env.example .env
   ```
5. Edit the `.env` file with your OpenAI API key

## Usage

1. Run the chat controller:
   ```
   python robot_chat.py
   ```

2. Enter natural language commands to control the robot:
   - "Go forward 3 spaces"
   - "Turn right and move forward 2 steps"
   - "Where is the robot right now?"
   - "Put the robot back in the center"

3. Type `help` to see the available direct commands
4. Type `exit` or `quit` to end the session

## Technical Details

The application:
1. Connects to the RobotGrid app via TCP (default: localhost:9999)
2. Uses an OpenAI-compatible LLM to translate natural language into specific robot commands
3. Sends the commands to the RobotGrid and shows the responses

Available robot commands:
- `forward <steps>`: Move the robot forward
- `backward <steps>`: Move the robot backward
- `turn left`: Rotate 90 degrees counter-clockwise 
- `turn right`: Rotate 90 degrees clockwise
- `position`: Get the current position and orientation
- `center`: Center the robot on the grid 