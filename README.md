# Company Chatbot

## Description
The Company Chatbot is a project designed to facilitate communication and integration with Google Sheets. It provides a backend service that handles requests and interacts with Google Sheets to manage data efficiently.

## Installation Instructions
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd company-chatbot
   ```
2. Create and activate the virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
To run the backend, execute the following command:
```bash
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```
To run the frontend, use:
```bash
python -m http.server 8080
```
Access the application through your web browser at `http://localhost:8000` for the backend and `http://localhost:8080` for the frontend.

## Important
- Replace your SERP API and GROQ API keys in the appropriate files before running the application.
- 

## File Descriptions
- **backend.py**: Contains the main backend logic for handling requests and integrating with Google Sheets.
- **google_sheets_integration.gs**: A Google Apps Script file for managing interactions with Google Sheets.
- **index.html**: The main HTML file for the frontend interface.
- **requirements.txt**: Lists the dependencies required for the project.

## Screenshots
*Leave space here to attach screenshots of the application and its interface.*
![CHATBOT-1](https://github.com/rajdesai1510/LEADGEN-TOOL-FOR-COMPANY-ANALYSIS/blob/main/images/CHATBOT-1.png)
![CHATBOT-2](https://github.com/rajdesai1510/LEADGEN-TOOL-FOR-COMPANY-ANALYSIS/blob/main/images/CHATBOT-2.png)
![GOOGLE-SHEETS-INTEGRATION](https://github.com/rajdesai1510/LEADGEN-TOOL-FOR-COMPANY-ANALYSIS/blob/main/images/GOOGLE_SHEETS.png)


## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License.
