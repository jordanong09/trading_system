# modules/data_loader.py - Simple volume converter

import pandas as pd
import os

class DataLoader:
    """Handle all data loading (Excel and CSV)"""
    
    @staticmethod
    def convert_volume(volume_str) -> float:
        """
        Convert volume strings like '35.48M', '1.5K', '2.3B' to actual numbers
        
        Examples:
            '35.48M' -> 35480000
            '1.5K' -> 1500
            '2.3B' -> 2300000000
            '1000' -> 1000
        """
        try:
            volume_str = str(volume_str).strip()
            
            # If it's already a number, return it
            if volume_str.replace('.', '').replace('-', '').isdigit():
                return float(volume_str)
            
            multipliers = {
                'K': 1_000,
                'M': 1_000_000,
                'B': 1_000_000_000,
                'T': 1_000_000_000_000
            }
            
            last_char = volume_str[-1].upper()
            
            if last_char in multipliers:
                number = float(volume_str[:-1])
                return int(number * multipliers[last_char])
            else:
                # Try to convert directly if no multiplier
                return float(volume_str)
                
        except Exception as e:
            print(f"   ⚠️  Warning: Could not convert volume '{volume_str}': {e}")
            return 0
    
    @staticmethod
    def load_data_from_excel(file_path: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
        """
        Load OHLCV data from Excel or CSV file
        """
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            print(f"📂 Loading file: {file_path}")
            print(f"   Format detected: {file_ext}")
            
            # Load based on file type
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
                print(f"   ✅ CSV file loaded")
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                print(f"   ✅ Excel file loaded (sheet: {sheet_name})")
            else:
                raise ValueError(f"Unsupported file format: {file_ext}. Use .csv or .xlsx")
            
            print(f"   📋 Columns found: {df.columns.tolist()}")
            
            # Validate Date column
            if 'Date' not in df.columns:
                print(f"   ❌ 'Date' column not found")
                raise ValueError(f"'Date' column not found")
            
            # Convert Date to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            
            # Validate required columns
            required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing = [col for col in required if col not in df.columns]
            if missing:
                print(f"   ❌ Missing columns: {missing}")
                raise ValueError(f"Missing columns: {missing}")
            
            # Convert Volume column from format like '35.48M' to numeric
            print(f"   🔄 Converting Volume column...")
            volume_sample = str(df['Volume'].iloc[0])
            print(f"      Sample: {volume_sample}")
            
            df['Volume'] = df['Volume'].apply(DataLoader.convert_volume)
            print(f"      ✅ Converted")
            
            # Ensure numeric types
            df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
            df['High'] = pd.to_numeric(df['High'], errors='coerce')
            df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            
            # Reorder columns
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            print(f"\n   ✅ Data loaded successfully!")
            print(f"   📊 Total rows: {len(df)}")
            print(f"   📅 Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
            print(f"   💰 Price range: ${df['Low'].min():.2f} to ${df['High'].max():.2f}")
            print(f"   📈 Volume range: {df['Volume'].min():,.0f} to {df['Volume'].max():,.0f}\n")
            
            return df
            
        except Exception as e:
            print(f"❌ Error loading data: {e}\n")
            return pd.DataFrame()