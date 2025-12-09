import streamlit as st
import pandas as pd
from datetime import datetime

def add_flight_page():

    # Load existing flights safely
    try:
        flights_df = pd.read_csv("flights.csv")
    except:
        flights_df = pd.DataFrame(columns=[
            "flight_id","airline","aircraft_type","arrival","departure",
            "turnaround_minutes","priority","country_type"
        ])

    # Input fields
    flight_id = st.text_input("Flight ID")
    airline = st.text_input("Airline")

    aircraft_type = st.selectbox(
        "Aircraft Type",
        ["A319","A320","A320neo" "A321", "A330","A340", "A350","A380", "B737","B747", "B777", "B787", "Other"]
    )

    country_type = st.selectbox(
        "Country Type",
        ["domestic", "international"]
    )

    # ------- DATETIME INPUT --------
    st.write("### Arrival Date & Time")
    arrival_date = st.date_input("Arrival Date")
    arrival_time = st.time_input("Arrival Time")

    st.write("### Departure Date & Time")
    departure_date = st.date_input("Departure Date")
    departure_time = st.time_input("Departure Time")

    # Combine date + time into a full datetime
    arrival = datetime.combine(arrival_date, arrival_time)
    departure = datetime.combine(departure_date, departure_time)
    # ---------------------------------------

    priority = st.selectbox("Priority", [1, 2])
    turnaround = st.number_input("Turnaround Minutes", min_value=10, max_value=180, value=45)

    # Add flight button
    if st.button("Add Flight"):
        try:
            # Validation
            if arrival >= departure:
                st.error("Arrival must be BEFORE departure!")
                return

            if flight_id.strip() == "":
                st.error("Flight ID cannot be empty.")
                return

            new_flight = {
                "flight_id": flight_id,
                "airline": airline,
                "aircraft_type": aircraft_type,
                "arrival": arrival,
                "departure": departure,
                "turnaround_minutes": turnaround,
                "priority": priority,
                "country_type": country_type
            }

            # FIX: append removed → using concat
            flights_df = pd.concat(
                [flights_df, pd.DataFrame([new_flight])],
                ignore_index=True
            )

            flights_df.to_csv("flights.csv", index=False)
            st.success("Flight added successfully!")

        except Exception as e:
            st.error(f"Error: {e}")
