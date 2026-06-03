# Vessel Performance Project Report

This report provides a comprehensive overview of the Vessel Performance Project, detailing the system from its inception to its final implementation and deployment strategy.

## 1. Problem Statement

Maritime shipping operations rely heavily on daily "Noon Reports" to track vessel positions, fuel consumption, speed, and weather conditions. Evaluating these reports against the Charter Party (CP) warranties—which dictate the agreed-upon fuel consumption and speed—is crucial for commercial efficiency and contractual compliance. 

Historically, analyzing these reports has been a manual, error-prone, and time-consuming process using complex spreadsheets. The **Vessel Performance Project** aims to automate this process. The system provides a centralized dashboard to parse raw noon reports, calculate key performance indicators (KPIs), compare actual performance against CP warranties, visualize trends, optimize voyage routing based on weather conditions, and generate comprehensive PDF reports.

## 2. Pipeline

The data pipeline for the Vessel Performance system is structured into four main stages:

1. **Ingestion**: The user uploads a raw Excel (`.xlsx`) noon report through the Streamlit interface.
2. **Parsing & Cleaning (`parser.py`)**: 
   - The application dynamically parses the Excel file, handling both standard row-based formats and transposed formats.
   - It normalizes column headers (e.g., standardizing `lat`, `latitude` -> `latitude`), handles missing values, and ensures data types are correct (converting coordinates to decimals, dates to datetime objects).
3. **Calculation & Analysis (`calculator.py` & `route_optimizer.py`)**:
   - Classifies the vessel's daily operation state (`Steaming`, `Maneuvering`, `Idle`).
   - Compares actual speed against the CP warranted speed.
   - Calculates the expected fuel consumption (LSFO) based on the operation state and compares it against actual consumption to find surpluses or deficits.
   - Re-computes Remaining On Board (ROB) values for LSFO and MGO dynamically.
   - Simulates alternative weather-optimized routes.
4. **Presentation (`app.py`, `charts.py`, `report_generator.py`)**:
   - Displays KPIs, charts, maps, and tabular logs in an interactive dashboard.
   - Allows exporting the processed insights into a well-formatted PDF report.

## 3. Methodology

### 3.1 Operations Classification
The system categorizes each day's operation based on the `remarks` and `engine_distance`. 
- **Idle**: If keywords like "anchor", "waiting", or "idle" are found, or if distance is negligible.
- **Maneuvering**: If keywords like "maneuver" are present.
- **Steaming**: If the distance covered is significant (e.g., > 50 nm).
This state dictates the expected fuel consumption (e.g., `cp_lsfo_steam` vs `cp_lsfo_idle`).

### 3.2 Performance Tracking
- **Speed Performance**: A simple variance calculation (`avg_speed - cp_speed`). The system highlights underperformance.
- **Fuel Performance**: Daily warranted LSFO is assigned based on the day's operational state. Actual `total_lsfo` is then subtracted from `warranted_lsfo` to quantify fuel saved or over-consumed.

### 3.3 Route Optimization
The system uses a synthetic, high-resolution 0.25-degree weather grid spanning the region. 
- **Weather Interpolation**: Inverse-distance weighting estimates wind (kts) and wave heights (m) at any coordinate.
- **Speed & Fuel Penalty Models**: Formulates speed reduction based on excessive wind/waves (e.g., -0.3 kts for every 5 kts of wind > 10 kts) and computes fuel consumption hikes per Beaufort scale increment.
- **Routing**: Computes the direct Great Circle route and an adjusted weather-avoidance route.

## 4. Implementation and Results

The project is implemented in **Python**, utilizing **Streamlit** for the frontend, **Pandas** for data manipulation, **Matplotlib** for visualization, and **Folium** for interactive spatial mapping.

### Key Features Implemented:
- **Performance Overview Tab**: Top-level metrics (Total Distance, Average Speed, Total LSFO Consumed) alongside an auto-generated narrative summarizing the voyage.
- **Daily Operations & Engine Summary**: Tabular views providing granular, day-by-day breakdowns of distance, speed, RPM, weather, and computed fuel ROBs.
- **Visual Analysis**: A suite of charts comparing actuals to CP terms. For example, the *LSFO ROB Drawdown Curve* and *Time Utilisation* pie charts.
- **Voyage Map**: Interactive map plotting reported positions, color-coded by operation type.
- **Route Optimizer**: Allows comparing a direct route with a weather-optimized route visually and quantitatively (calculating MT of fuel saved).
- **PDF Generation**: Uses `report_generator.py` to compile the analysis into a downloadable PDF document.

## 5. How to Use the Project

### Running the Application Locally
1. Ensure you have Python installed.
2. Navigate to the project directory (`c:\Users\Asus\vessel_performance`).
3. Create and activate a virtual environment (optional but recommended).
4. Install dependencies using `pip install -r requirements.txt`.
5. Run the app using the command: `streamlit run app.py`.

### Using the Dashboard
1. **Upload Data**: Once the app is running in your browser, upload your Noon Report (`.xlsx`) via the sidebar.
2. **Set CP Terms**: Adjust the Charter Party terms (Vessel Name, Warranted Speed, Warranted Consumption rates, and Opening ROBs) in the sidebar.
3. **Generate Report**: Click the "Generate Report" button.
4. **Analyze**: Navigate through the tabs (Performance Overview, Visual Analysis, Route Optimizer, etc.) to review insights.
5. **Export**: Scroll to the bottom and click "Generate & Download PDF" to save a local copy of the compiled report.

## 6. Deployment

To deploy this application to production, you can use **Streamlit Community Cloud** (which is free and connects directly to a GitHub repository) or containerize it using Docker for deployment on cloud providers like AWS, Azure, or Heroku. 
For local, daily use, executing `streamlit run app.py` on your machine provides an immediate, robust environment.
