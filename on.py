from app import app
from utils.db import init_db, seed_sample_data

if __name__ == '__main__':
    app.run(debug=True)
    init_db() 
    seed_sample_data()