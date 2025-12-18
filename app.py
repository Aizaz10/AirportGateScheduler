import streamlit as st
import pandas as pd
import plotly.express as px
from scheduler import schedule_flights
from add_flight import add_flight_page

st.set_page_config(page_title="Airport Gate Scheduler", layout="wide")
st.title("Airport Gate Scheduler")

# Sidebar menu
st.sidebar.title("Aizaz Air Control")
menu = st.sidebar.radio("Menu", ["Dashboard", "Run Scheduler", "Add Flight"])

# Global buffers
st.sidebar.header("Settings")
pre_buffer = st.sidebar.number_input("Pre-arrival buffer (min)", min_value=0, max_value=60, value=0)
post_buffer = st.sidebar.number_input("Post-departure buffer (min)", min_value=0, max_value=120, value=0)

# DASHBOARD
if menu == "Dashboard":
    st.header("Real-Time Airport Activity Dashboard")

    try:
        flights_df = pd.read_csv("flights.csv")
        gates_df = pd.read_csv("gates.csv")
    except:
        st.info("Upload files from 'Run Scheduler' page or add new flights first.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Flights", len(flights_df))
    col2.metric("Domestic Flights", flights_df[flights_df["country_type"]=="domestic"].shape[0])
    col3.metric("International Flights", flights_df[flights_df["country_type"]=="international"].shape[0])

    st.subheader("Active Flight Board")
    st.dataframe(
        flights_df[[
            "flight_id", "airline", "aircraft_type",
            "arrival", "departure", "country_type", "priority"
        ]],
        use_container_width=True
    )

    st.subheader("Flights by Gate Type")
    gate_counts = gates_df["country_type"].value_counts().reset_index()
    gate_counts.columns = ["Gate Type", "Count"]

    fig = px.pie(gate_counts, names="Gate Type", values="Count",
                 title="Gate Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Flights per Airline")
    airline_count = flights_df["airline"].value_counts().reset_index()
    airline_count.columns = ["Airline", "Flights"]

    fig2 = px.bar(airline_count, x="Airline", y="Flights",
                  title="Airline Activity")
    st.plotly_chart(fig2, use_container_width=True)


# ADD FLIGHT PAGE

elif menu == "Add Flight":
    st.header("Add New Flight")
    add_flight_page()   

# RUN SCHEDULER PAGE

elif menu == "Run Scheduler":
    st.header("Upload files to run scheduler")

    flights_file = st.file_uploader("Upload flights.csv", type=["csv"])
    gates_file = st.file_uploader("Upload gates.csv", type=["csv"])

    if st.button("Run Scheduler"):
        if not flights_file or not gates_file:
            st.error("Please upload both flights.csv and gates.csv")
            st.stop()

        flights_df = pd.read_csv(flights_file)
        gates_df = pd.read_csv(gates_file)

        try:
            result_df = schedule_flights(
                flights_df, gates_df,
                post_buffer_min=post_buffer,
                pre_buffer_min=pre_buffer
            )
        except Exception as e:
            st.error(f"Scheduling error: {e}")
            st.stop()

        st.success("Scheduling completed successfully!")

        # KPIs
        total = len(result_df)
        unassigned = result_df[result_df['status']=='unassigned'].shape[0]
        st.metric("Total flights", total)
        st.metric("Unassigned flights", unassigned)

        # Colors
        airlines = result_df['airline'].unique().tolist()
        color_map = {air: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                     for i,air in enumerate(airlines)}
        result_df['color'] = result_df['airline'].map(color_map)

        st.subheader("Gate Assignments")
        st.dataframe(result_df[[
            'flight_id','airline','aircraft_type','arrival','departure',
            'priority','country_type','assigned_gate','status'
        ]], use_container_width=True)

        # Download
        csv = result_df.to_csv(index=False)
        st.download_button("Download assignments.csv", csv, "assignments.csv")

        # Gantt
        st.subheader("Gate Timeline (Gantt)")
        gantt = result_df[result_df['status']=='assigned'].copy()
        if gantt.empty:
            st.info("No assigned flights to show.")
        else:
            gantt['Start'] = pd.to_datetime(gantt['arrival'])
            gantt['Finish'] = pd.to_datetime(gantt['departure']) + \
                              pd.to_timedelta(gantt['turnaround_minutes'], unit='m') + \
                              pd.to_timedelta(post_buffer, unit='m')

            fig = px.timeline(
                gantt,
                x_start="Start",
                x_end="Finish",
                y="assigned_gate",
                color="airline",
                hover_data=["flight_id","aircraft_type","priority","country_type"]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

        # Unassigned list
        if unassigned > 0:
            st.subheader("Unassigned Flights")
            st.dataframe(result_df[
                result_df['status']=='unassigned'
            ][['flight_id','airline','arrival','departure','aircraft_type','priority','country_type']])
