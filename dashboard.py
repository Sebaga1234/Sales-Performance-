import pandas as pd
import streamlit as st
import plotly.express as px
from faker import Faker
import random
from datetime import datetime, timedelta
import os

# Set page config as the first Streamlit command
st.set_page_config(page_title="Al-Solutions Sales Analytics Dashboard", layout="wide")

# Initialize Faker
fake = Faker()

# Define request types and corresponding page URLs
request_pages = {
    "Scheduled Demo": "/scheduledemo.php",
    "Promotional Event": "/event.php",
    "Virtual Assistant": "/virtualassistant.php",
    "Prototyping Solution": "/prototype.php"
}

# Job types for analysis
job_types = ["Software Assistance", "AI Integration", "Custom Development", "Consulting"]

# List of countries for simulation
countries = ["US", "UK", "FR", "DE", "JP", "CN", "BR", "IN", "AU", "CA"]

# Define product mapping globally
product_mapping = {
    "Scheduled Demo": "Demo Product",
    "Promotional Event": "Event Product",
    "Virtual Assistant": "VA Product",
    "Prototyping Solution": "Prototype Product",
    "Other": "General Product"
}

# Function to generate web server log data
def generate_web_logs(num_records=1000):
    logs = []
    start_date = datetime(2025, 1, 1)
    
    for _ in range(num_records):
        timestamp = fake.date_time_between(start_date=start_date, end_date=start_date + timedelta(days=90))
        ip_address = fake.ipv4()
        method = "GET"
        page = random.choice(list(request_pages.values()) + ["/index.html", "/contact.php"])
        status_code = random.choice([200, 304, 404])
        country = random.choice(countries)
        job_type = random.choice(job_types) if page in request_pages.values() else "None"
        
        log_entry = {
            "timestamp": timestamp,
            "ip_address": ip_address,
            "method": method,
            "page": page,
            "status_code": status_code,
            "country": country,
            "job_type": job_type
        }
        logs.append(log_entry)
    
    df = pd.DataFrame(logs)
    df['request_type'] = df['page'].map({v: k for k, v in request_pages.items()}).fillna("Other")
    df.to_csv("al_solutions_web_logs.csv", index=False)
    return df

# Check if CSV exists, else generate data with validation
@st.cache_data
def load_and_preprocess_data():
    if os.path.exists("al_solutions_web_logs.csv"):
        df = pd.read_csv("al_solutions_web_logs.csv")
        required_columns = ['timestamp', 'ip_address', 'page', 'status_code', 'country', 'job_type']
        if not all(col in df.columns for col in required_columns):
            return None  # Indicate invalid CSV; handle in main script
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
    else:
        df = generate_web_logs(1000)

    # Add hour, week, product name, and session data
    df['hour'] = df['timestamp'].dt.hour
    df['week'] = df['timestamp'].dt.isocalendar().week

    # Use global product_mapping
    df['product_name'] = df['request_type'].map(product_mapping)

    # Compute session data
    df = df.sort_values(['ip_address', 'timestamp'])
    df['time_diff'] = df.groupby('ip_address')['timestamp'].diff().dt.total_seconds().fillna(3600) / 60  # Minutes
    df['new_session'] = (df['time_diff'] > 30).astype(int)  # New session if > 30 minutes
    df['session_id'] = df.groupby('ip_address')['new_session'].cumsum()
    df['session_id'] = df['ip_address'] + '_' + df['session_id'].astype(str)

    # Compute pages per session and session duration
    session_stats = df.groupby('session_id').agg(
        pages_per_session=('page', 'nunique'),
        session_start=('timestamp', 'min'),
        session_end=('timestamp', 'max')
    ).reset_index()
    session_stats['session_duration'] = (session_stats['session_end'] - session_stats['session_start']).dt.total_seconds() / 60  # Minutes
    df = df.merge(session_stats[['session_id', 'pages_per_session', 'session_duration']], on='session_id')
    return df

# Load and preprocess data, handle errors after set_page_config
df = load_and_preprocess_data()
if df is None:
    st.error("CSV missing required columns. Generating new data.")
    df = generate_web_logs(1000)
    # Reprocess to ensure consistency
    df['hour'] = df['timestamp'].dt.hour
    df['week'] = df['timestamp'].dt.isocalendar().week
    df['product_name'] = df['request_type'].map(product_mapping)
    df = df.sort_values(['ip_address', 'timestamp'])
    df['time_diff'] = df.groupby('ip_address')['timestamp'].diff().dt.total_seconds().fillna(3600) / 60
    df['new_session'] = (df['time_diff'] > 30).astype(int)
    df['session_id'] = df.groupby('ip_address')['new_session'].cumsum()
    df['session_id'] = df['ip_address'] + '_' + df['session_id'].astype(str)
    session_stats = df.groupby('session_id').agg(
        pages_per_session=('page', 'nunique'),
        session_start=('timestamp', 'min'),
        session_end=('timestamp', 'max')
    ).reset_index()
    session_stats['session_duration'] = (session_stats['session_end'] - session_stats['session_start']).dt.total_seconds() / 60
    df = df.merge(session_stats[['session_id', 'pages_per_session', 'session_duration']], on='session_id')

# Streamlit Dashboard
st.title("Al-Solutions Product Sales Analytics")

# Create tabs
overview_tab, main_tab, eda_tab = st.tabs(["Overview", "Main", "EDA"])

# Overview Tab
with overview_tab:
    st.header("Dashboard Overview")
    st.markdown("""
    This dashboard analyzes web server logs to evaluate Al-Solutions' sales strategy for AI-powered software solutions. 
    It provides insights into customer interactions by country, request types, job types, products, and session engagement, 
    supporting marketing and sales performance assessment.
    """)
    
    # KPIs on filtered data 
    # Filters
    st.sidebar.header("Filters")

    st.sidebar.markdown("""
    """)

    selected_country = st.sidebar.multiselect("Select Country", 
                                             options=countries, 
                                             default=[], 
                                             key="main_country")
    selected_request_type = st.sidebar.multiselect("Select Request Type", 
                                                  options=list(request_pages.keys()) + ["Other"], 
                                                  default=[], 
                                                  key="main_request")
    selected_job_type = st.sidebar.multiselect("Select Job Type", 
                                              options=job_types + ["None"], 
                                              default=[], 
                                              key="main_job")
    selected_hours = st.sidebar.multiselect("Select Request Hour", 
                                           options=list(range(24)), 
                                           default=[], 
                                           key="main_hours")
    selected_products = st.sidebar.multiselect("Select Product", 
                                              options=list(product_mapping.values()), 
                                              default=[], 
                                              key="main_product")
    session_duration_range = st.sidebar.slider("Session Duration (Minutes)", 
                                              min_value=0, max_value=int(df['session_duration'].max()) + 1, 
                                              value=(0, int(df['session_duration'].max()) + 1), 
                                              key="main_duration")
    
    # Filter data
    countries_to_filter = selected_country if selected_country else countries
    request_types_to_filter = selected_request_type if selected_request_type else list(request_pages.keys()) + ["Other"]
    job_types_to_filter = selected_job_type if selected_job_type else job_types + ["None"]
    hours_to_filter = selected_hours if selected_hours else list(range(24))
    products_to_filter = selected_products if selected_products else list(product_mapping.values())
    
    filtered_df = df[(df['country'].isin(countries_to_filter)) & 
                     (df['request_type'].isin(request_types_to_filter)) & 
                     (df['job_type'].isin(job_types_to_filter)) & 
                     (df['hour'].isin(hours_to_filter)) & 
                     (df['product_name'].isin(products_to_filter)) & 
                     (df['session_duration'].between(session_duration_range[0], session_duration_range[1]))]
    

    # KPIs on filtered data
    # Define revenue per conversion request
    revenue_mapping = {
        "Scheduled Demo": 500,  # $500 per request
        "Virtual Assistant": 300,  # $300 per request
        "Prototyping Solution": 1000  # $1000 per request
    }
    # Calculate revenue and profit for conversion requests
    filtered_df['revenue'] = filtered_df['request_type'].map(revenue_mapping).fillna(0)
    filtered_df['profit'] = filtered_df['revenue'] * 0.3  # 30% profit margin
    
    conversion_requests = len(filtered_df[filtered_df['request_type'].isin(["Scheduled Demo", "Virtual Assistant", "Prototyping Solution"])])
    total_requests = len(filtered_df)
    conversion_rate = (conversion_requests / total_requests * 100) if total_requests > 0 else 0
    total_revenue = filtered_df['revenue'].sum()
    total_profit = filtered_df['profit'].sum()
    job_stats = filtered_df[filtered_df['job_type'] != "None"].groupby('job_type').size()
    avg_call_target = job_stats.mean() if not job_stats.empty else 0
    
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Conversion Rate", f"{conversion_rate:.2f}%")
    col2.metric("Total Revenue", f"${total_revenue:,.2f}")
    col3.metric("Total Profit", f"${total_profit:,.2f}")
    col4.metric("Average Call Target", f"{avg_call_target:.2f}")
    
    st.markdown("""
    The **Main** tab is for interactive visualizations and filters, and the **EDA** tab is for detailed exploratory data analysis.
    """)


# Main Tab
with main_tab:
    st.header("Main Analysis")
    st.write(f"Showing {len(filtered_df)} records after filtering.")

    # First Row: Original Visualizations
    st.subheader("Primary Visualizations")
    col1, col2, col3, col4 = st.columns(4)
    
    # Bar Chart: Requests by Country
    with col1:
        country_requests = filtered_df['country'].value_counts().reset_index()
        country_requests.columns = ['Country', 'Requests']
        if not country_requests.empty:
            fig_bar = px.bar(country_requests, x='Country', y='Requests', title="Requests by Country",
                             color='Country', color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.write("No data for Requests by Country.")
    
    # Pie Chart: Request Type Distribution
    with col2:
        request_counts = filtered_df['request_type'].value_counts().reset_index()
        request_counts.columns = ['Request Type', 'Count']
        if not request_counts.empty:
            fig_pie = px.pie(request_counts, values='Count', names='Request Type', 
                             title="Request Type Distribution",
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.write("No data for Request Type Distribution.")
    
    # Bar Chart: Job Types
    with col3:
        job_counts = filtered_df[filtered_df['job_type'] != "None"]['job_type'].value_counts().reset_index()
        job_counts.columns = ['Job Type', 'Count']
        if not job_counts.empty:
            fig_job_bar = px.bar(job_counts, x='Job Type', y='Count', title="Job Types Requested",
                                 color='Job Type', color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_job_bar, use_container_width=True)
        else:
            st.write("No data for Job Types Requested.")
    
    # Scatterplot: Request Times
    with col4:
        hourly_requests = filtered_df.groupby('hour').size().reset_index(name='Requests')
        if not hourly_requests.empty:
            fig_scatter = px.scatter(hourly_requests, x='hour', y='Requests', 
                                     title="Requests by Hour",
                                     labels={'hour': 'Hour of Day', 'Requests': 'Number of Requests'},
                                     color='Requests', color_continuous_scale='Viridis')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.write("No data for Requests by Hour.")
    
    # Second Row: New Visualizations
    st.subheader("Detailed Visualizations")
    col5, col6, col7, col8 = st.columns(4)
    
    # Heatmap: Country vs. Request Type
    with col5:
        country_request_counts = filtered_df.groupby(['country', 'request_type']).size().reset_index(name='Count')
        if not country_request_counts.empty:
            fig_heatmap = px.density_heatmap(country_request_counts, x='country', y='request_type', z='Count', 
                                             title="Country vs. Request Type",
                                             color_continuous_scale='Blues')
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.write("No data for Country vs. Request Type.")
    
    # Pie Chart: Product Name vs. Engaged User
    with col6:
        product_user_counts = filtered_df.groupby('product_name')['ip_address'].nunique().reset_index(name='Engaged Users')
        if not product_user_counts.empty:
            fig_product_pie = px.pie(product_user_counts, values='Engaged Users', names='product_name', 
                                     title="Product Name vs. Engaged Users",
                                     color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_product_pie, use_container_width=True)
        else:
            st.write("No data for Product Name vs. Engaged Users.")
    
    # Line Chart: Pages per Session vs. Session Duration
    with col7:
        session_stats = filtered_df.groupby('pages_per_session')['session_duration'].mean().reset_index()
        if not session_stats.empty:
            fig_session_line = px.line(session_stats, x='pages_per_session', y='session_duration', 
                                       title="Pages per Session vs. Session Duration",
                                       labels={'pages_per_session': 'Pages per Session', 'session_duration': 'Avg Session Duration (Minutes)'},
                                       markers=True)
            st.plotly_chart(fig_session_line, use_container_width=True)
        else:
            st.write("No data for Pages per Session vs. Session Duration.")
    
    # Histogram: Session Duration Distribution
    with col8:
        if not filtered_df.empty:
            fig_histogram = px.histogram(filtered_df, x='session_duration', title="Session Duration Distribution",
                                         labels={'session_duration': 'Session Duration (Minutes)'},
                                         color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig_histogram, use_container_width=True)
        else:
            st.write("No data for Session Duration Distribution.")

# EDA Tab
with eda_tab:
    st.header("Exploratory Data Analysis")
    
    # Detailed Data View
    st.subheader("Detailed Web Server Logs")
    st.dataframe(filtered_df, use_container_width=True, height=400)
    
    # Summary Statistics
    st.subheader("Summary Statistics")
    if not filtered_df.empty:
        mean_requests_per_country = filtered_df.groupby('country').size().mean()
        std_requests_per_country = filtered_df.groupby('country').size().std()
        job_stats = filtered_df[filtered_df['job_type'] != "None"].groupby('job_type').size()
        mean_job_requests = job_stats.mean() if not job_stats.empty else 0
        std_job_requests = job_stats.std() if not job_stats.empty else 0
        st.write(f"Mean requests per country: {mean_requests_per_country:.2f}")
        st.write(f"Standard deviation of requests per country: {std_requests_per_country:.2f}")
        st.write(f"Median requests per country: {filtered_df.groupby('country').size().median():.2f}")
        st.write(f"Mean requests per job type: {mean_job_requests:.2f}")
        st.write(f"Standard deviation of requests per job type: {std_job_requests:.2f}")
        st.write(f"Correlation (Pages per Session vs. Session Duration): {filtered_df[['pages_per_session', 'session_duration']].corr().iloc[0,1]:.2f}")
    else:
        st.write("No data available for the selected filters.")
