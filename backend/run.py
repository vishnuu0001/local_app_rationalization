import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

app = create_app()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_mode, host='0.0.0.0', port=5000, use_reloader=debug_mode)
