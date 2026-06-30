## Getting Started (Local Development Setup)

To run this project on your local machine, you will need to clone the repository and set up a Python Virtual Environment. 

### Step 1: Clone the Repository
Open your terminal and run:

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
git checkout dev
```

(Note: We are currently working in the dev branch for Phase 1 development).

### Step 2: Set up the Python Environment
Choose the instructions below based on your operating system:

Option A: For Windows (VS Code Local)
Open the terminal in VS Code (cmd or powershell) and run:

```bash
Create the sandbox: python -m venv venv

Activate it: .\venv\Scripts\activate

Install dependencies: pip install -r requirements.txt
```

Option B: For Linux (DEVASC VM) or macOS
Open your terminal and run:

```bash
Create the sandbox: python3 -m venv venv

Activate it: source venv/bin/activate

Install dependencies: pip install -r requirements.txt
```

### Step 3: Run the Server
Once the requirements are installed and the (venv) tag is active in your terminal, start the Flask backend server:

```bash
python app.py
```

(If using the Linux VM, you may need to type python3 app.py).

The database will automatically initialize itself. Open your web browser and navigate to http://127.0.0.1:5000 to view the application!

### Project Structure
- app.py: The Python Flask REST API and SQLite database initialization.
- index.html: The main user interface.
- js/: Frontend logic (Search, UI rendering, Data management).
- css/: Custom styling overrides.
- data/: Raw JSON data containing the RP module information.
- requirements.txt: Python dependency list.

### Important Git Rules
- Before committing new code, ensure you do not upload your local database or virtual environment. The .gitignore file is already configured to block venv/ and *.db files.
- Never merge your own code directly to main. Always open a Pull Request (PR) and have a teammate review it first.