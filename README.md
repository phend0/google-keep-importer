# Google Keep Note Importer

A Python tool to automate the importing of Google Keep notes (JSON format) from a Google Takeout export into a new Google Keep account.

## How it Works

Since Google Keep does not have an official public API for creating notes, this script uses **Playwright** to automate a real Google Chrome instance. 

1. It launches Chrome with remote debugging enabled.
2. You log in manually to your target Google account.
3. Once logged in, the script takes over and "types" your notes into Keep one by one.

## Prerequisites

- **Python 3.7+**
- **Google Chrome** installed on your system.
- **Google Takeout Export**: 
  - Go to [Google Takeout](https://takeout.google.com/).
  - Select only **Google Keep**.
  - Choose **JSON** as the format.
  - Download and extract the zip file.

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/google-keep-import.git
   cd google-keep-import
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Prepare your notes**:
   - Create a folder named `notes` in the project directory.
   - Copy all the `.json` files from your Google Takeout `Keep` folder into this `notes` folder.

## Usage

1. **Run the script**:
   ```bash
   python import_keep.py
   ```

2. **Follow the prompts**:
   - A Chrome window will open.
   - Log in to your Google account.
   - Go back to the terminal and press **Enter**.
   - Watch as the script imports your notes!

## Troubleshooting

- **Selector Errors**: If Google updates the Keep UI, the script might fail to find the "Title" or "Body" inputs. You may need to update the CSS selectors at the top of `import_keep.py`.
- **Slowness**: The script includes small delays (`wait_for_timeout`) to ensure Google Keep can process the typing. Do not lower these too much or notes may be skipped.
- **Duplicate Notes**: If you restart the script, it uses `keep_progress.json` to resume where it left off. If you delete that file, it will start from the beginning.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
