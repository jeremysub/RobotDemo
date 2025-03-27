import os
import socket
import json
import sys
import openai
from dotenv import load_dotenv

# Load environment variables from .env file (for API keys)
load_dotenv()

# Configuration
TCP_HOST = "localhost"  # The server's hostname or IP address
TCP_PORT = 12345        # The port used by the server (matching RobotGrid)
API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Available robot commands
AVAILABLE_COMMANDS = [
    "forward <steps>",
    "backward <steps>",
    "turn left",
    "turn right",
    "position",
    "center"
]

class RobotController:
    def __init__(self, host=TCP_HOST, port=TCP_PORT):
        self.host = host
        self.port = port
        
        # Initialize OpenAI with the older pattern that's more compatible
        if not API_KEY:
            print("Warning: OPENAI_API_KEY not set in .env file")
        
        # Set API key directly on the openai module (legacy pattern)
        openai.api_key = API_KEY
        if API_BASE != "https://api.openai.com/v1":
            openai.api_base = API_BASE
        
        # System prompt for the LLM
        self.system_prompt = """
You are a robot control assistant that translates natural language into specific robot commands.

AVAILABLE COMMANDS (exactly as written, one per line):
- forward <number>
- backward <number>
- turn left
- turn right
- position
- center

EXAMPLES:
User: "What's my location?"
Assistant:
position

User: "Move forward 3 steps and then turn right"
Assistant:
forward 3
turn right

User: "Go to the center of the grid"
Assistant:
center

IMPORTANT RULES:
1. ONLY respond with the exact commands from the list above
2. Each command must be on its own line
3. Do not include ANY explanations, apologies, or other text
4. If you're not sure what command to use, use "position" to check current status
5. Position is in a 15x15 grid (0-14, 0-14)
"""
        
        # Initialize conversation history
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def send_command(self, command):
        """Send a command to the TCP server and return the response"""
        # Create a new connection for each command since the server disconnects after each one
        try:
            # Create a new socket for this command
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.host, self.port))
            
            # Handle special commands
            if command.lower() == "position":
                # The server expects GET_POSITION
                print("Requesting position information...")
                s.sendall("GET_POSITION\n".encode())
                response = s.recv(1024).decode().strip()
                print(f"Raw position response: '{response}'")
                
                # Close the socket
                s.close()
                
                try:
                    parts = response.split()
                    if len(parts) >= 3:
                        x, y, dir_val = int(parts[0]), int(parts[1]), int(parts[2])
                        direction = {0: "Up", 90: "Right", 180: "Down", 270: "Left"}.get(dir_val, str(dir_val))
                        return f"Position: ({x}, {y}), Facing: {direction}"
                    else:
                        return f"Invalid position data: {response}"
                except Exception as e:
                    print(f"Error parsing position: {e}")
                    return f"Raw position data: {response}"
            
            elif command.lower() == "center":
                print("Centering robot...")
                s.sendall("CENTER\n".encode())
                response = s.recv(1024).decode().strip()
                s.close()
                return "Robot centered"
                
            else:
                # Normal commands: FORWARD n, BACKWARD n, TURN LEFT, TURN RIGHT
                parts = command.strip().split()
                server_command = " ".join(parts).upper()
                
                print(f"Sending command: '{server_command}'")
                s.sendall(f"{server_command}\n".encode())
                response = s.recv(1024).decode().strip()
                s.close()
                print(f"Response: '{response}'")
                
                if response:
                    return response
                else:
                    return "Command executed"
                
        except ConnectionRefusedError:
            print(f"Connection refused: Make sure the RobotGrid application is running on {self.host}:{self.port}")
            return "Error: Connection refused"
        except socket.timeout:
            print(f"Connection timed out: Could not connect to {self.host}:{self.port}")
            return "Error: Connection timeout"
        except Exception as e:
            print(f"Error sending command: {e}")
            return f"Error: {e}"
    
    def process_natural_language(self, user_input):
        """Process natural language input using the LLM and convert to robot commands"""
        # Add user input to message history
        self.messages.append({"role": "user", "content": user_input})
        
        try:
            # Get response from LLM using the legacy pattern
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=self.messages,
                temperature=0.1,  # Lower temperature for more deterministic responses
                max_tokens=150,
            )
            
            # Extract the assistant's response
            assistant_response = response.choices[0].message.content.strip()
            
            # Validate that the response contains valid commands
            valid_commands = []
            for line in assistant_response.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line matches a valid command pattern
                valid = False
                if line in ["turn left", "turn right", "position", "center"]:
                    valid = True
                elif line.startswith("forward ") or line.startswith("backward "):
                    parts = line.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        valid = True
                
                if valid:
                    valid_commands.append(line)
            
            # If no valid commands were found, use position as fallback
            if not valid_commands:
                print("Warning: LLM response contained no valid commands, using 'position' as fallback")
                valid_commands = ["position"]
                
            # Join valid commands back into a response
            final_response = "\n".join(valid_commands)
            
            # Add final response to message history
            self.messages.append({"role": "assistant", "content": final_response})
            
            # Return the valid commands
            return final_response
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return "position"  # Fallback to a safe command
    
    def execute_commands(self, commands):
        """Execute a list of robot commands and return the results"""
        results = []
        
        # Process each command
        for command in commands.split('\n'):
            command = command.strip()
            if not command:
                continue
            
            print(f"Executing: {command}")
            result = self.send_command(command)
            results.append(f"{command} → {result}")
        
        return '\n'.join(results)
    
    def run_chat_loop(self):
        """Run the main chat loop"""
        print("🤖 Robot Chat Controller 🤖")
        print("Type 'exit' or 'quit' to end the session.")
        print("Type 'help' to see available direct commands.")
        
        # Test if we can connect to the server
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(5)
            test_socket.connect((self.host, self.port))
            test_socket.close()
            print(f"RobotGrid server is available at {self.host}:{self.port}")
        except Exception as e:
            print("\n❌ Could not connect to the RobotGrid application.")
            print(f"   Error: {e}")
            print("   Make sure it's running before starting this client.")
            print("   The RobotGrid server should be listening on port 12345.")
            return
        
        # Get the robot's current position
        try:
            position_info = self.send_command("position")
            print(f"Initial robot status: {position_info}")
        except Exception as e:
            print(f"Could not get initial position: {e}")
            return
        
        print("\n✅ Successfully connected to the RobotGrid!")
        print("You can now enter natural language commands to control the robot.")
        print("Examples:")
        print("  - 'Where is the robot?'")
        print("  - 'Move forward 3 steps and turn right'")
        print("  - 'Go back to the center of the grid'")
        
        while True:
            try:
                # Get user input
                user_input = input("\n🧠 Enter your instruction: ").strip()
                
                # Check for exit command
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                # Check for help command
                if user_input.lower() == 'help':
                    print("\nAvailable direct commands:")
                    for cmd in AVAILABLE_COMMANDS:
                        print(f"- {cmd}")
                    continue
                
                # Direct command mode (bypass LLM for testing)
                if user_input.lower().startswith("direct:"):
                    command = user_input[7:].strip()
                    print(f"\n⚡ Executing direct command: {command}")
                    result = self.send_command(command)
                    print(f"Response: {result}")
                    continue
                
                # Process natural language with LLM
                print("\n🔄 Processing your request...")
                llm_response = self.process_natural_language(user_input)
                print("\n🤖 Generated commands:")
                print(llm_response)
                
                # Execute the commands
                print("\n📡 Robot responses:")
                results = self.execute_commands(llm_response)
                print(results)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                # Don't break, try again
        
        print("Session ended. Goodbye!")

if __name__ == "__main__":
    controller = RobotController()
    controller.run_chat_loop() 