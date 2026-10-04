"""
Database Module
Handles SQLite persistence for energy consumption and savings data
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any

class DatabaseManager:
    """Manages SQLite database for energy tracking"""
    
    def __init__(self, db_path: str = 'smart_energy.db'):
        """Initialize database and create tables if they don't exist"""
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self):
        """Create necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for energy consumption logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                device TEXT,
                state TEXT,
                power_watts REAL,
                energy_kwh REAL,
                cost_usd REAL
            )
        ''')
        
        # Table for session summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME,
                end_time DATETIME,
                total_energy_kwh REAL,
                total_cost_usd REAL,
                estimated_savings_usd REAL,
                carbon_footprint_kg REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def log_energy(self, device: str, state: str, power: float, energy: float, cost: float):
        """Log energy consumption for a device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO energy_logs (device, state, power_watts, energy_kwh, cost_usd) VALUES (?, ?, ?, ?, ?)",
            (device, state, power, energy, cost)
        )
        conn.commit()
        conn.close()
        
    def save_session_summary(self, summary: Dict[str, Any]):
        """Save a summary of the current session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO session_summaries 
            (start_time, end_time, total_energy_kwh, total_cost_usd, estimated_savings_usd, carbon_footprint_kg)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            summary.get('start_time'),
            summary.get('end_time'),
            summary.get('total_energy_kwh'),
            summary.get('total_cost_usd'),
            summary.get('estimated_savings_usd'),
            summary.get('carbon_footprint_kg')
        ))
        conn.commit()
        conn.close()
        
    def get_historical_data(self, limit: int = 100) -> List[Dict]:
        """Get recent logs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM session_summaries ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
