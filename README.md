Installation:
- Clone the present repo in your local file system
- Create the virtual environment in your machine: python -m venv <name of your virtual environment>
- Activate the environment using the right command for your terminal
- Write in your terminal: pip install -r requirements.txt
- (Optional) Follow instructions in MAS_Unity_Visualization repo to see how to do a 3D visualization

Execution:
- (Optional) Run an instance of the MAS_Unity_Visualization project beforehand to see 3D visualization
- Run script "main.py"
- Close the animation window at any point to stop the run of the simulation and advance to results
- Close results windows in order to advance
- Wait for system to send data over to Unity project
- A server not available error occurs when:
    - The Unity project was not executed before the sending of data, run it to see 3D animation
    - The server's URL does not match with the one from the Unity project, change it to Unity's URL

