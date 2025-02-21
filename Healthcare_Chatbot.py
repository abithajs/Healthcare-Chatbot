import os
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_float import *
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re
from dotenv import load_dotenv
import mysql.connector
from sqlalchemy import create_engine
from sqlalchemy import text

# Initialize float feature
float_init()

# Custom CSS for the chat container and icon
st.markdown("""
<style>
.stPopover {
    position: fixed;
    bottom: 50px;
    right: 50px;
}
.stPopover button {
    font-size: 24px; /* Reset to a smaller size */
    padding: 10px;
    background-color: #ffffff;
    border: 2px solid red;
    border-radius: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 60px;  /* Set a fixed width */
    height: 60px; /* Set a fixed height */
    overflow: hidden;
}
.stPopover button::before {
    content: '👩‍⚕️';
    font-size: 24px; /* Increase only the emoji size */
}
</style>
""", unsafe_allow_html=True)

# Chat popover with icon
with st.popover("", use_container_width=False):
    st.title("Healthcare Chatbot 👩🏻‍⚕️🤖")

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [{"role": "assistant", "content": "Hello! I am your helpful healthcare assistant. How can I assist you today?"}]
    if "flow" not in st.session_state:
        st.session_state.flow = None
    if "menu" not in st.session_state:
        st.session_state.menu = None
    if "show_menu" not in st.session_state:
        st.session_state.show_menu = False
    if "previous_selection" not in st.session_state:
        st.session_state.previous_selection = None
        
    
    # Containers for layout management
    chat_history = st.container()  # Container for chat messages
    menu_container = st.container()  # Container for menu options
    pre_booking_container = st.container()  # Container for pre-booking flow
    reschedule_container=st.container()
    edit_appointment_container=st.container()
    chat_input_placeholder = st.empty()  # Empty container for chat input

    # Function to update the flow based on user selection
    def on_radio_change():
        option = st.session_state.menu
        if option == "📅 Pre Booking":
            st.session_state.flow = "pre_booking"
            st.session_state.messages.append({"role": "assistant", "content": "You have selected Pre-Booking. Let's start by selecting the specialization."})
        elif option == "🔄 Reschedule Appointment":
            st.session_state.flow = "reschedule"
            st.session_state.messages.append({"role": "assistant", "content": "You have selected Reschedule Appointment. Please enter the patient's mail ID to proceed."})
        elif option == "✏️ Edit Appointment":
            st.session_state.flow = "edit_appointment"
            st.session_state.messages.append({"role": "assistant", "content": "You have selected Edit Appointment. Please enter the patient's mail ID to proceed."})

    # Display chat history
    with chat_history:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input - Use chat input placeholder at the end of the script
    with chat_input_placeholder:
        query = st.chat_input("Say something (e.g., 'hi', 'book appointment')")

        if query:
            st.session_state.messages.append({"role": "user", "content": query})

            query_lower = query.lower()
            healthcare_keywords = ["book", "appointment", "find slot", "fix appointment", "reschedule", "edit appointment",
                                    "schedule", "doctor", "health","Need to schedule appointment","APPOINTMENT",
                                    "NEED TO BOOK APPOINTMENT","FIND","edit","slot","find","book an appointment","book appointment",
                                    "appoinment","appoitment","schedle","need to book an available slot","I need to reschedule the appoitnemnt",
                                    "need to schedule","need to fix an appointment","yes","Yes","YES"]

            if query_lower in ["hi", "hello", "hey"]:
                response = ("Hi there! How are you doing today? 😊\n\n"
                            "How can I assist you? Please select an option below:")
                st.session_state.show_menu = True  # Show menu immediately after greeting
            elif any(keyword in query_lower for keyword in healthcare_keywords):
                response = "Got it! Here's what I can help you with. Please select an option below:"
                st.session_state.show_menu = True  # Show menu after healthcare-related query
            else:
                response = "I didn't understand that. Could you please try again with a healthcare-related query?"
                st.session_state.show_menu = False  # Don't show menu if the input is unrelated

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()  # Trigger a rerun after processing input

    # Display the options menu if show_menu is True
    with menu_container:
       if st.session_state.show_menu:
           st.radio(
            "Please select an option to proceed:",
            ["📅 Pre Booking", "🔄 Reschedule Appointment", "✏️ Edit Appointment"],
            key="menu",
            label_visibility="collapsed",
            on_change=on_radio_change
        )

    # Load the main .env file
    load_dotenv()

    # Manually load password from the 'eymp_passwor.env' file
    def load_password_from_file(password_file):
        with open(password_file, 'r') as file:
            password = file.readline().strip()  # Reading the first line and removing any extra spaces/newlines
        return password

    # Email configuration
    SMTP_SERVER = "smtp.gmail.com"  
    SMTP_PORT = 587
    EMAIL_ADDRESS = "abitha.js@beauroi.com" 
    EMAIL_PASSWORD = load_password_from_file('SMTP_password.env')

   # Create SQLAlchemy engine
    engine = create_engine("mysql+pymysql://root:Abi%407522@localhost:3307/healthcare_chatbot")

    # Load data from specialization table
    specialization_query = "SELECT Specialization_ID, Specialization, Department FROM master_table"
    specialization_data = pd.read_sql(specialization_query, con=engine)

    # Load data from appointment table
    appointments_query = """
        SELECT `Patient ID`, `Patient Name`, Age, Gender, `Phone Number`, Email, Date, 
            Time, Status, Specialization_ID, Doctor_ID, `Slot Number` 
        FROM appointment_data
    """
    appointments_data = pd.read_sql(appointments_query, con=engine)

    # Load data from doctor schedules table
    doctor_schedules_query = """
        SELECT Doctor_ID, Doctor_Name, Specialization_ID, `Starting Time`, `Ending Time`, `Patients Count` 
        FROM doctor_schedules
    """
    doctor_schedules = pd.read_sql(doctor_schedules_query, con=engine)

    # Function to validate phone number
    def is_valid_phone(phone):
        regex = r'^\+?\d{10,15}$'
        return re.match(regex, phone) is not None

    # Function to validate email
    def is_valid_email(email):
        regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(regex, email) is not None

    # Function to validate IDs
    def check_valid_ids(specialization_id, doctor_id):
        specialization_exists = not specialization_data[specialization_data['Specialization_ID'] == specialization_id].empty
        doctor_exists = not doctor_schedules[doctor_schedules['Doctor_ID'] == doctor_id].empty
        return specialization_exists and doctor_exists

    # Function to handle selection process dynamically
    def handle_selection(selection_key, options, label):
        selected_option = st.selectbox(label, options, key=selection_key)
        current_selection = (selection_key, selected_option)

        if current_selection != st.session_state.previous_selection:
            st.session_state.previous_selection = current_selection

        return selected_option

   # Function to save or update bookings in MySQL
    def save_booking(booking_data):
        # Find the specialization ID from the specialization name
        specialization_id = specialization_data[specialization_data['Specialization'] == booking_data['Specialization']].iloc[0]['Specialization_ID']
        
        # Find the doctor ID from the selected doctor's name
        doctor_id = doctor_schedules[doctor_schedules['Doctor_Name'] == booking_data['Doctor']].iloc[0]['Doctor_ID']
        
        # Update the booking data with proper IDs
        booking_data['Specialization_ID'] = specialization_id
        booking_data['Doctor_ID'] = doctor_id
        
        # Add the Doctor's name again to the booking data for calendar invite
        doctor_name = booking_data['Doctor']  
        
        del booking_data['Specialization']
        del booking_data['Doctor']
        
        # Connect to the database and insert the new booking data
        try:
            with engine.connect() as connection:
                # Convert the booking data to a DataFrame for insertion
                booking_df = pd.DataFrame([booking_data])
                
                # Insert the booking data into the 'appointment_data' table
                booking_df.to_sql('appointment_data', con=connection, if_exists='append', index=False)
        except Exception as e:
            print(f"Error occurred while saving the booking: {e}")

        # Validate the IDs against the master_table and doctor_schedules
        if not check_valid_ids(booking_data['Specialization_ID'], booking_data['Doctor_ID']):
            print("Invalid Specialization ID or Doctor ID!")
            return

    # Function to map IDs to names
    def map_ids_to_names(booking_data):
        try:
            doctor_name = doctor_schedules.loc[
                doctor_schedules['Doctor_ID'] == booking_data['Doctor_ID'], 
                'Doctor_Name'
            ].values[0]
        except IndexError:
            doctor_name = "Unknown Doctor"

        try:
            specialization_name = specialization_data.loc[
                specialization_data['Specialization_ID'] == booking_data['Specialization_ID'], 
                'Specialization'
            ].values[0]
        except IndexError:
            specialization_name = "Unknown Specialization"

        booking_data['Doctor'] = doctor_name
        booking_data['Specialization'] = specialization_name
        return booking_data


    # Function to create ICS calendar invite
    def create_calendar_invite(booking_data):
        try:
        # Map IDs to names (assuming this function exists in your codebase)
            booking_data = map_ids_to_names(booking_data)
            
            # Try parsing the date in multiple formats
            try:
                # First try "DD-MM-YYYY" format
                start_time = datetime.strptime(f"{booking_data['Date']} {booking_data['Time']}", "%d-%m-%Y %H:%M")
            except ValueError:
                # If that fails, try "YYYY-MM-DD" format
                start_time = datetime.strptime(f"{booking_data['Date']} {booking_data['Time']}", "%Y-%m-%d %H:%M")
            
            # Calculate the end time for a 15-minute appointment
            end_time = start_time + timedelta(minutes=15)
            
            # Create the event description
            event_description = f"Appointment with Dr. {booking_data['Doctor']} for {booking_data['Specialization']}."

            # Create ICS content
            ics_content = (
                f"BEGIN:VCALENDAR\n"
                f"VERSION:2.0\n"
                f"PRODID:-//Healthcare Appointment//EN\n"
                f"BEGIN:VEVENT\n"
                f"UID:{booking_data['Email']}-{start_time}\n"
                f"DTSTAMP:{start_time.strftime('%Y%m%dT%H%M%S')}\n"
                f"DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}\n"
                f"DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}\n"
                f"SUMMARY:Healthcare Appointment\n"
                f"DESCRIPTION:{event_description}\n"
                f"LOCATION:Healthcare Clinic\n"
                f"BEGIN:VALARM\n"
                f"TRIGGER:-PT30M\n"  # Reminder 30 minutes before
                f"DESCRIPTION:Reminder for your appointment with Dr. {booking_data['Doctor']}\n"
                f"ACTION:DISPLAY\n"
                f"END:VALARM\n"
                f"END:VEVENT\n"
                f"END:VCALENDAR"
            )
            
            return ics_content
        except ValueError as e:
            # Handle date parsing errors
            st.error(f"Error parsing date/time: {e}")
            return None
        except Exception as e:
            # Handle general errors
            st.error(f"Error creating calendar invite: {e}")
            return None

    # Function to send an email notification with calendar invite
    def send_email_notification(to_email, subject, body, ics_content=None):
        try:
            # Create email message
            message = MIMEMultipart()
            message["From"] = EMAIL_ADDRESS
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            # Attach ICS file if provided
            if ics_content:
                ics_filename = "appointment.ics"
                ics_attachment = MIMEBase("application", "octet-stream")
                ics_attachment.set_payload(ics_content)
                encoders.encode_base64(ics_attachment)
                ics_attachment.add_header("Content-Disposition", f"attachment; filename={ics_filename}")
                message.attach(ics_attachment)

            # Connect to SMTP server and send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(message)

            st.success(f"Notification sent to {to_email}")
        except Exception as e:
            st.error(f"Failed to send notification: {e}")

    # Function to validate the IDs before saving
    def check_valid_ids(specialization_id, doctor_id):
        # Check if the specialization ID and doctor ID are valid in the respective tables
        valid_specialization = specialization_data[specialization_data['Specialization_ID'] == specialization_id].shape[0] > 0
        valid_doctor = doctor_schedules[doctor_schedules['Doctor_ID'] == doctor_id].shape[0] > 0
        
        return valid_specialization and valid_doctor

                
    # Function to collect patient details
    def collect_patient_details():
        patient_name = st.text_input("Enter Patient Name")
        patient_age = st.number_input("Enter Patient Age", min_value=1, max_value=120, step=1)
        gender = st.selectbox("Select Gender", ["M", "F"], index=0, format_func=lambda x: "Male" if x == "M" else "Female")
        patient_phone = st.text_input("Enter Phone Number (10 digits)")
        patient_email = st.text_input("Enter Email ID")

         # Validate phone number and email
        phone_valid = is_valid_phone(patient_phone)
        email_valid = is_valid_email(patient_email)

        # Proceed only if all fields are valid
        if patient_name and patient_age and phone_valid and email_valid:
            return {
                "Patient Name": patient_name,
                "Age": patient_age,
                "Phone Number": patient_phone,
                "Email": patient_email,
                "Gender": gender
            }
        else:
            # Show validation warnings if fields are not valid
            if not patient_name:
                st.warning("Please enter the patient's name.")
            if not patient_age:
                st.warning("Please enter the patient's age.")
            if not phone_valid:
                st.warning("Please enter a valid 10-digit phone number.")
            if not email_valid:
                st.warning("Please enter a valid email address.")
            return None  # Return None if there are invalid details
        
        # Function to Generate Patient ID
    def generate_patient_id(appointment_data, email):
        # Check if the patient already exists
        existing_patient = appointment_data[
            (appointment_data['Email'] == email)
        ]

        if not existing_patient.empty:
            # Return the existing Patient ID
            return existing_patient.iloc[0]['Patient ID']

        # Generate a new Patient ID if the patient does not exist
        if not appointment_data.empty:
            # Safely drop NaN values and get the max Patient ID
            last_patient_id = appointment_data['Patient ID'].dropna().max()

            if pd.isna(last_patient_id) or not last_patient_id.startswith("PHC"):
                # If the last Patient ID is invalid or doesn't start with "PHC", reset numbering
                last_number = 0
            else:
                # Extract the numeric part from the last Patient ID and increment it
                last_number = int(last_patient_id[3:])
        else:
            # If the dataset is empty, start from 0
            last_number = 0

        # Create the new Patient ID
        new_patient_id = f"PHC{last_number + 1:02d}"
        return new_patient_id
    
    def check_and_update_status(email):
        """Check if the user has any pending appointments without a status and prompt for update."""
        with engine.connect() as connection:
            check_query = text("""
                SELECT Status FROM appointment_data WHERE Email = :email AND (Status IS NULL OR Status = '')
            """)
            result = connection.execute(check_query, {"email": email}).fetchone()

            if result:
                st.warning("You have a previous appointment without a status update. Please update it before proceeding.")
                action = st.selectbox("Select Action", ["Closed", "No-Show"])
                confirm_action = st.selectbox(f"Are you sure you want to mark as {action}?", ["No", "Yes"])

                if confirm_action == "Yes":
                    update_query = text("""
                        UPDATE appointment_data
                        SET Status = :status
                        WHERE Email = :email AND (Status IS NULL OR Status = '')
                    """)
                    connection.execute(update_query, {"status": action, "email": email})
                    connection.commit()
                    st.success(f"Appointment marked as '{action}' successfully.")
                elif confirm_action == "No":
                    st.error("❌ You must update the previous appointment before proceeding with a new booking.")
                    st.stop()  # Prevents further execution and keeps the user on the same page.

    # Function to get booked slots and count from MySQL
    def get_booked_slots_and_count(date, doctor_name, doctor_schedules):
        # Map doctor name to Doctor_ID
        doctor_id = doctor_schedules[doctor_schedules["Doctor_Name"] == doctor_name].iloc[0]["Doctor_ID"]

        # Query to fetch booked slots for the given doctor and date
        query = f"""
            SELECT Time 
            FROM appointment_data
            WHERE Doctor_ID = '{doctor_id}' AND Date = '{date.strftime('%Y-%m-%d')}'
        """
        booked_slots_df = pd.read_sql(query, con=engine)

        # Extract booked time slots as a list
        booked_slots = booked_slots_df['Time'].tolist()

        # Count the number of booked appointments
        booked_count = len(booked_slots)

        return booked_slots, booked_count

    # Function to get available slots before booking
    def get_available_slots_pre_booking(date, doctor_name, doctor_schedules):
        # Fetch doctor's schedule
        doctor_schedule = doctor_schedules[doctor_schedules["Doctor_Name"] == doctor_name].iloc[0]
        start_time = datetime.strptime(doctor_schedule['Starting Time'].strip(), "%H:%M")
        end_time = datetime.strptime(doctor_schedule['Ending Time'].strip(), "%H:%M")
        slot_duration = timedelta(minutes=30)

        # Generate all possible time slots
        time_slots = []
        while start_time + slot_duration <= end_time:
            time_slots.append(start_time.strftime('%H:%M'))
            start_time += slot_duration

        # Fetch booked slots and count for that doctor on the selected date
        booked_slots, booked_count = get_booked_slots_and_count(date, doctor_name, doctor_schedules)

        # Remove booked slots from the available slots
        available_slots = [slot for slot in time_slots if slot not in booked_slots]

        # Add slot numbers for the available slots
        available_slots_with_numbers = []
        for slot in available_slots:
            slot_number = time_slots.index(slot) + 1  # Slot number based on the original time slots
            available_slots_with_numbers.append({"time": slot, "slot_number": f"Slot {slot_number}"})

        return available_slots_with_numbers, booked_slots


    # Function to get available slots for editing an appointment
    def get_available_slots(date, doctor_name, doctor_schedules, current_time=None):
        # Fetch doctor's schedule
        doctor_schedule = doctor_schedules[doctor_schedules["Doctor_Name"] == doctor_name].iloc[0]
        start_time = datetime.strptime(doctor_schedule['Starting Time'], "%H:%M")
        end_time = datetime.strptime(doctor_schedule['Ending Time'], "%H:%M")
        slot_duration = timedelta(minutes=30)

        # Generate all time slots within the doctor's working hours
        time_slots = []
        while start_time + slot_duration <= end_time:
            time_slots.append(start_time.strftime('%H:%M'))
            start_time += slot_duration

        # Get booked slots for the doctor on the selected date
        booked_slots, _ = get_booked_slots_and_count(date, doctor_name, doctor_schedules)

        # Remove booked slots from the available time slots and exclude the current time (if rescheduling)
        available_slots = [slot for slot in time_slots if slot not in booked_slots]

        if current_time:
            # If rescheduling, exclude the current time from the available slots
            available_slots = [slot for slot in available_slots if slot != current_time]

        # Include slot numbers for the available slots
        available_slots_with_numbers = []
        for slot in available_slots:
            slot_number = time_slots.index(slot) + 1  # Calculate based on original time slots
            available_slots_with_numbers.append({"time": slot, "slot_number": f"Slot {slot_number}"})

        return available_slots_with_numbers, booked_slots

   # Pre Booking Flow
    with pre_booking_container:
        if st.session_state.flow == "pre_booking":
            # Select specialization from available specializations
            specializations = specialization_data[['Specialization_ID', 'Specialization']].drop_duplicates()
            selected_specialization = handle_selection("specialization_select", specializations['Specialization'].unique(), "Specialization")
            
            if selected_specialization:
                # Find doctors for the selected specialization
                specialization_id = specializations[specializations['Specialization'] == selected_specialization].iloc[0]['Specialization_ID']
                doctors = doctor_schedules[doctor_schedules['Specialization_ID'] == specialization_id]['Doctor_ID'].unique()
                
                # Map doctor IDs to doctor names
                doctor_names = doctor_schedules[doctor_schedules['Doctor_ID'].isin(doctors)]['Doctor_Name'].unique()
                selected_doctor = handle_selection("doctor_select", doctor_names, "Doctor")

                if selected_doctor:
                    patient_details = collect_patient_details()
                    if patient_details:
                        # 🔹 Check if the user has an unresolved previous appointment
                        check_and_update_status(patient_details['Email'])
        
                        today_date = datetime.today().date()
                        date = st.date_input("Select Appointment Date", min_value=today_date)

                         # Get available slots for the selected doctor and date
                        available_slots_with_numbers, booked_slots = get_available_slots_pre_booking(date, selected_doctor, doctor_schedules)

                        if available_slots_with_numbers:  # Check if there are available slots
                            # Assuming current_time is retrieved dynamically, we simulate current time for this example
                            current_time = datetime.now().strftime("%H:%M")  # Get current time in "%H:%M" format

                            # Convert current time to datetime object for comparison
                            current_time_obj = datetime.strptime(current_time, "%H:%M")

                             # Check if the selected date is today or in the future
                            if date == today_date:  # If today's date is selected, filter out past slots
                                # Filter out slots that have already passed based on the current time
                                available_slots_with_numbers = [
                                    slot for slot in available_slots_with_numbers
                                    if datetime.strptime(slot['time'], "%H:%M") > current_time_obj  # Show only slots that are after the current time
                                ]

                            # Display the available slots with slot numbers
                            available_slots_display = [
                                    f"{slot['time']}" for slot in available_slots_with_numbers
                                ]
                            selected_time = st.selectbox("Select Appointment Time", available_slots_display)

                            if selected_time and st.button("Book Appointment"):
                                # Extract the selected slot time
                                selected_slot = next(slot for slot in available_slots_with_numbers if slot['time'] == selected_time)
                                slot_number = selected_slot['slot_number']  # Extract the slot number from the available slots

                                # Generate the Patient ID
                                patient_id = generate_patient_id(
                                    appointments_data,
                                    patient_details['Email']
                                )

                                
                                booking_data = {
                                    **patient_details,
                                    "Patient ID": patient_id,
                                    "Specialization": selected_specialization,
                                    "Doctor": selected_doctor,
                                    "Date": date,
                                    "Time": selected_time,
                                    "Slot Number": slot_number  # Slot number for email and internal use
                                }

                                save_booking(booking_data)  # Save the booking

                                # Create the ICS calendar invite
                                ics_content = create_calendar_invite(booking_data)

                                # Send booking notification email with calendar invite
                                email_subject = "Appointment Confirmation"
                                email_body = (
                                    f"Dear {booking_data['Patient Name']},\n\n"
                                    f"Your appointment has been successfully booked:\n"
                                    f"Doctor: Dr. {booking_data['Doctor']}\n"
                                    f"Specialization: {booking_data['Specialization']}\n"
                                    f"Date: {booking_data['Date']}\n"
                                    f"Time: {booking_data['Time']}\n"
                                    f"Slot Number: {booking_data['Slot Number']}\n\n"
                                    f"Thank you for choosing our services!"
                                )
                                send_email_notification(booking_data['Email'], email_subject, email_body, ics_content)

                                # Success message with patient info
                                st.success(
                                    f"Appointment successfully booked!\n\n"
                                    f"**Patient Name:** {patient_details['Patient Name']}\n"
                                    f"**Contact Number:** {patient_details['Phone Number']}\n"
                                    f"**Email:** {patient_details['Email']}\n"
                                    f"**Doctor:** Dr. {selected_doctor}\n"
                                    f"**Specialization:** {selected_specialization}\n"
                                    f"**Date:** {date}\n"
                                    f"**Time:** {selected_time}\n"
                                    f"**Slot Number:** {slot_number}"
                                )
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": (
                                        f"Appointment booked for **{patient_details['Patient Name']}** "
                                        f"(Phone: {patient_details['Phone Number']}, Email: {patient_details['Email']}) "
                                        f"with Dr. {selected_doctor} for {selected_specialization} on {date} at {selected_time}."
                                    )
                                })
                                # Asking if the user needs further assistance
                                st.session_state.messages.append({
                                "role": "assistant", 
                                "content": "Is there anything else I can assist you with?"
                                })

                                st.session_state.flow = None
                                st.session_state.show_menu = False  # Hide the options after booking
                            
                        # Go Back to Menu button
                        back_button = st.button("Go Back to Menu")
                        if back_button:
                            st.session_state.flow = None
                            st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your helpful healthcare assistant. How can I assist you today?"}]

    # Edit Appointment Flow
    with edit_appointment_container:
        if st.session_state.flow == "edit_appointment":
            patient_email_to_edit = st.text_input("Enter Patient Email to Edit Appointment:", key="edit_patient_email")

            # Validate email immediately
            if patient_email_to_edit and not is_valid_email(patient_email_to_edit):
                st.error("Please enter a valid email address.")    

            elif patient_email_to_edit:
                    query = """
                    SELECT `Patient ID`, `Patient Name`, Age, Gender, `Phone Number`, Email, Date, 
                        Time, Status, Specialization_ID, Doctor_ID, `Slot Number`
                    FROM appointment_data
                    WHERE Email = %(patient_email)s
                    ORDER BY Date DESC, Time DESC
                    LIMIT 1
                """
                    with engine.connect() as connection:
                        appointment_to_edit = pd.read_sql(query, con=connection, params={"patient_email": patient_email_to_edit})

                    if not appointment_to_edit.empty:
                        # Display Current Appointment Details
                        st.subheader(f"Current Appointment Details for {patient_email_to_edit}")
                        appointment_info = appointment_to_edit[['Patient Name', 'Age', 'Phone Number', 'Email', 'Doctor_ID', 'Specialization_ID', 'Date', 'Time']]
                        st.dataframe(appointment_info)

                        st.subheader("Edit Appointment Details")

                        # Pre-fill Specialization based on current appointment
                        selected_specialization_id = appointment_to_edit['Specialization_ID'].iloc[0]
                        selected_specialization = specialization_data[specialization_data['Specialization_ID'] == selected_specialization_id]['Specialization'].iloc[0]

                        # Step 1: Pre-fill Specialization
                        specializations = specialization_data[['Specialization_ID', 'Specialization']].drop_duplicates()
                        selected_specialization = handle_selection("specialization_select", specializations['Specialization'].unique(), "Specialization")

                        if selected_specialization:
                            # Map Specialization name to Specialization_ID
                            specialization_id = specializations[specializations['Specialization'] == selected_specialization].iloc[0]['Specialization_ID']

                            # Step 2: Pre-fill Doctor based on Specialization_ID
                            doctors = doctor_schedules[doctor_schedules['Specialization_ID'] == specialization_id]['Doctor_ID'].unique()
                            doctor_names = doctor_schedules[doctor_schedules['Doctor_ID'].isin(doctors)]['Doctor_Name'].unique()

                            # Select the doctor based on current appointment details
                            selected_doctor = handle_selection("doctor_select", doctor_names, "Doctor")

                            if selected_doctor:
                                # Map Doctor name to Doctor_ID
                                doctor_id = doctor_schedules[doctor_schedules['Doctor_Name'] == selected_doctor].iloc[0]['Doctor_ID']

                                # Step 3: Display Doctor's Schedule (Working Hours)
                                doctor_schedule = doctor_schedules[doctor_schedules['Doctor_ID'] == doctor_id].iloc[0]
                                start_time = doctor_schedule['Starting Time']
                                end_time = doctor_schedule['Ending Time']
                                st.write(f"Doctor {selected_doctor}'s Schedule:")
                                st.write(f"Working Hours: {start_time} - {end_time}")

                                # Step 4: Pre-fill Date for Appointment
                                #current_date = pd.to_datetime(appointment_to_edit['Date'].iloc[0]).date()
                                # Check the format of the date from the database (e.g., if it's in dd-mm-yyyy or yyyy-mm-dd)
                                date_str = appointment_to_edit['Date'].iloc[0]
                                # Attempt to parse with both formats
                                try:
                                    current_date = pd.to_datetime(date_str, format='%d-%m-%Y')  # Try dd-mm-yyyy
                                except ValueError:
                                    current_date = pd.to_datetime(date_str, format='%Y-%m-%d')  # Fallback to yyyy-mm-dd

                                # Now you can use current_date
                                current_date = current_date.date()
                                new_date = st.date_input("Select New Appointment Date", min_value=datetime.today().date(), key="edit_appointment_date")

                                # Get available slots for the selected doctor and date (User selects slot manually)
                                current_time = appointment_to_edit['Time'].iloc[0]  # The current booked time
                                available_slots_with_numbers, booked_slots = get_available_slots(new_date, selected_doctor, doctor_schedules, current_time)

                                if available_slots_with_numbers:  # Check if there are available slots
                                    # Assuming current_time is retrieved dynamically, we simulate current time for this example
                                    current_time = datetime.now().strftime("%H:%M")  # Get current time in "%H:%M" format

                                    # Convert current time to datetime object for comparison
                                    current_time_obj = datetime.strptime(current_time, "%H:%M")

                                    # Check if the selected date is today or in the future
                                    if new_date == datetime.today().date():   # If today's date is selected, filter out past slots
                                        # Filter out slots that have already passed based on the current time
                                        available_slots_with_numbers = [
                                            slot for slot in available_slots_with_numbers
                                            if datetime.strptime(slot['time'], "%H:%M") > current_time_obj  # Show only slots that are after the current time
                                        ]
                                
                                    available_slots_display = [
                                        f"{slot['time']}" for slot in available_slots_with_numbers
                                    ]
                                    selected_time = st.selectbox("Select New Appointment Time", available_slots_display)
                                else:
                                    st.warning("No available slots for the selected doctor on this date. Please choose a different date.")
                                    selected_time = None

                                # Pre-fill Patient Name and Age
                                patient_name = st.text_input("Patient Name", value=appointment_to_edit['Patient Name'].iloc[0], key="edit_patient_name")
                                age = st.number_input("Age", value=int(appointment_to_edit['Age'].iloc[0]), key="edit_age")
                                current_phone = str(appointment_to_edit['Phone Number'].iloc[0])
                                new_phone = st.text_input("Edit Phone Number (10 digits)", value=current_phone, key="edit_phone_number")
                                new_email = st.text_input("Edit Email ID", value=appointment_to_edit['Email'].iloc[0], key="edit_email")

                                if selected_time:  
                                        # Ensure that a new time is selected
                                        selected_slot = next(slot for slot in available_slots_with_numbers if slot['time'] == selected_time)
                                        slot_number = selected_slot['slot_number']  # Extract the slot number from the available slots
                                else:
                                        st.warning("Please select a valid time slot.")
                                        
                                if is_valid_phone(new_phone) and is_valid_email(new_email):        
                                    if st.button("Update Appointment", key="update_appointment_button"):
                                         # Query to check for appointments with NULL or empty Status
                                        check_query = text("""
                                            SELECT `Date`, `Time`, `Slot Number`
                                            FROM appointment_data
                                            WHERE Email = :email AND (Status IS NULL OR Status = '')
                                        """)
                                        
                                        # Fetch the result of the query
                                        with engine.connect() as connection:
                                            result = connection.execute(check_query, {"email": patient_email_to_edit}).fetchall()

                                        if result:  # If there are appointments to update with NULL/empty status
                                            # Get the last appointment that matches the criteria
                                            appointment_index = result[-1]  # Last matching row

                                            # Access the values using tuple indices
                                            current_date = appointment_index[0]  # Index for 'Date'
                                            current_time = appointment_index[1]  # Index for 'Time'

                                            # SQL query to update the appointment
                                            update_query =text("""
                                                UPDATE appointment_data
                                                SET `Patient Name` = :patient_name, Age = :age, `Phone Number` = :phone_number, 
                                                    Email = :email, Date = :date, Time = :time, Specialization_ID = :specialization_id, 
                                                    Doctor_ID = :doctor_id, `Slot Number` = :slot_number
                                                WHERE Email = :email_to_edit                                                               
                                                AND `Date` = :current_date
                                                AND `Time` = :current_time
                                                LIMIT 1;  -- Ensuring only the last row is updated
                                            """)
                                            parameters = {
                                                "patient_name": patient_name,
                                                "age": age,
                                                "phone_number": new_phone,
                                                "email": new_email,
                                                "date": new_date.strftime("%Y-%m-%d"),
                                                "time": selected_time,
                                                "specialization_id": specialization_id,
                                                "doctor_id": doctor_id,
                                                "slot_number": slot_number,
                                                "email_to_edit": patient_email_to_edit,
                                                "current_date": current_date,  # Use the correct current date value
                                                "current_time": current_time   # Use the correct current time value
                                            }

                                            with engine.connect() as connection:
                                                with connection.begin():  # Ensure the transaction is committed
                                                    connection.execute(update_query, parameters)

                                            # Prepare booking data for email and calendar invite
                                            booking_data = { 
                                            "Patient Name": patient_name,
                                            "Age": age,
                                            "Phone Number": new_phone,
                                            "Email": new_email,
                                            "Doctor_ID": doctor_id,
                                            "Doctor": selected_doctor,
                                            "Specialization_ID": specialization_id,
                                            "Specialization": selected_specialization,
                                            "Date": new_date,
                                            "Time": selected_time,
                                            "Slot Number": slot_number
                                            }

                                            # Create ICS calendar invite
                                            ics_content = create_calendar_invite(booking_data)

                                            # Send notification email with updated details
                                            email_subject = "Appointment Updated"
                                            email_body = (
                                                f"Dear {booking_data['Patient Name']},\n\n"
                                                f"Your appointment has been successfully updated:\n"
                                                f"Doctor: Dr. {booking_data['Doctor']}\n"
                                                f"Specialization: {booking_data['Specialization']}\n"
                                                f"Date: {booking_data['Date']}\n"
                                                f"Time: {booking_data['Time']}\n\n"
                                                f"Slot Number: {booking_data['Slot Number']}\n\n"
                                                f"Thank you for choosing our services!"
                                            )
                                            send_email_notification(booking_data['Email'], email_subject, email_body, ics_content)

                                            # Success message
                                            st.success(
                                                f"Appointment for {booking_data['Patient Name']} successfully updated!\n\n"
                                                f"**Patient Name:** {booking_data['Patient Name']}\n"
                                                f"**Contact Number:** {new_phone}\n"
                                                f"**Email:** {new_email}\n"
                                                f"**Doctor:** Dr. {booking_data['Doctor']}\n"
                                                f"**Specialization:** {booking_data['Specialization']}\n"
                                                f"**New Date:** {new_date}\n"
                                                f"**New Time:** {selected_time}\n"
                                                f"**Slot Number:** {slot_number}"
                                            )
                                            # Asking if the user needs further assistance
                                            st.session_state.messages.append({
                                            "role": "assistant", 
                                            "content": "Is there anything else I can assist you with?"
                                            })

                                            st.session_state.flow = None
                                            st.session_state.show_menu = False  # Hide the options after booking
                                else:
                                     st.warning("Please enter a valid phone number and email before updating the appointment.")
                            else:
                                st.warning("No doctors found for the selected specialization.")
                    else:
                       st.warning("No appointment found for email: {patient_email_to_edit}.")

                     # Go Back to Menu button
                    back_button = st.button("Go Back to Menu", key="back_to_menu_button")
                    if back_button:
                        st.session_state.flow = None
                        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you today?"}]

    # Reschedule Flow (using Specialization_ID and Doctor_ID)
    with reschedule_container:
        if st.session_state.flow == "reschedule":
            patient_email_to_reschedule = st.text_input("Enter Patient Email to Reschedule:",key="edit_patient_email")
            
            if patient_email_to_reschedule:
                if not is_valid_email(patient_email_to_reschedule):
                    st.error("Please enter a valid email address.")
                else:
                    # Fetch current date
                    current_date = datetime.today().date()
                    # Calculate the date range for the past 3 days
                    ten_days_ago = current_date - timedelta(days=30)

                    # Fetch appointments with Status = 'No-Show' for the given email, and filter by date range
                    reschedule_appointments = appointments_data[
                        (appointments_data['Email'] == patient_email_to_reschedule) & 
                        (appointments_data['Status'] == 'No-Show') &
                        (
                            pd.to_datetime(appointments_data['Date'], format='%Y-%m-%d', errors='coerce').dt.date >= ten_days_ago
                        ) &  # Within last 3 days
                        (
                            pd.to_datetime(appointments_data['Date'], format='%Y-%m-%d', errors='coerce').dt.date < current_date
                        )  # Exclude current or future dates
                    ]

                    if not reschedule_appointments.empty:
                        st.subheader(f"Missed Appointments for {patient_email_to_reschedule}")
                        # Display missed appointments
                        st.dataframe(reschedule_appointments[['Patient Name', 'Age', 'Phone Number', 'Email', 'Gender', 'Date', 'Time', 'Doctor_ID', 'Specialization_ID']])

                        # Fetch and pre-fill patient details
                        patient_name = st.text_input("Patient Name", value=reschedule_appointments['Patient Name'].values[0])
                        age = st.number_input("Age", value=int(reschedule_appointments['Age'].values[0]))
                        gender = st.text_input("Gender", value=reschedule_appointments['Gender'].values[0])
                        phone_number = st.text_input("Phone Number (10 digits)", value=int(reschedule_appointments['Phone Number'].values[0]))
                        email = st.text_input("Email ID", value=reschedule_appointments['Email'].values[0])

                        # Step 1: Select Specialization
                        st.subheader("Select New Appointment Details")
                        specializations = specialization_data[['Specialization_ID', 'Specialization']].drop_duplicates()
                        selected_specialization = st.selectbox(
                            "Select Specialization", 
                            specializations['Specialization'].unique()
                        )

                        if selected_specialization:
                            # Step 2: Map selected specialization to Specialization_ID
                            specialization_id = specializations[specializations['Specialization'] == selected_specialization].iloc[0]['Specialization_ID']

                            # Step 3: Select Doctor based on Specialization_ID
                            doctors = doctor_schedules[doctor_schedules['Specialization_ID'] == specialization_id]['Doctor_ID'].unique()
                            doctor_names = doctor_schedules[doctor_schedules['Doctor_ID'].isin(doctors)]['Doctor_Name'].unique()
                            selected_doctor = st.selectbox("Select Doctor", doctor_names)

                            if selected_doctor:
                                # Step 4: Map selected doctor to Doctor_ID
                                doctor_id = doctor_schedules[doctor_schedules['Doctor_Name'] == selected_doctor].iloc[0]['Doctor_ID']

                                # Step 5: Display Doctor's Schedule
                                doctor_schedule = doctor_schedules[doctor_schedules['Doctor_ID'] == doctor_id].iloc[0]
                                start_time = doctor_schedule['Starting Time']
                                end_time = doctor_schedule['Ending Time']
                                st.write(f"Doctor {selected_doctor}'s Schedule:")
                                st.write(f"Working Hours: {start_time} - {end_time}")

                                # Step 6: Select New Appointment Date
                                new_date = st.date_input("Select New Appointment Date", min_value=datetime.today().date())
                                #current_time = reschedule_appointments['Time'].values[0]  # Get the time of the missed appointment
                                # Get available slots for the selected doctor and date (User selects slot manually)
                                current_time = reschedule_appointments['Time'].iloc[0]  # The current booked time
                                available_slots_with_numbers, booked_slots = get_available_slots(new_date, selected_doctor, doctor_schedules, current_time)

                                if available_slots_with_numbers:  # Check if there are available slots
                                        # Assuming current_time is retrieved dynamically, we simulate current time for this example
                                        current_time = datetime.now().strftime("%H:%M")  # Get current time in "%H:%M" format

                                        # Convert current time to datetime object for comparison
                                        current_time_obj = datetime.strptime(current_time, "%H:%M")

                                        # Check if the selected date is today or in the future
                                        if new_date == datetime.today().date():   # If today's date is selected, filter out past slots
                                            # Filter out slots that have already passed based on the current time
                                            available_slots_with_numbers = [
                                                slot for slot in available_slots_with_numbers
                                                if datetime.strptime(slot['time'], "%H:%M") > current_time_obj  # Show only slots that are after the current time
                                            ]
                                    
                                        available_slots_display = [
                                            f"{slot['time']}" for slot in available_slots_with_numbers
                                        ]
                                        selected_time = st.selectbox("Select New Appointment Time", available_slots_display)
                                else:
                                        st.warning("No available slots for the selected doctor on this date. Please choose a different date.")
                                        selected_time = None
                                
                                if selected_time:  
                                            # Ensure that a new time is selected
                                            selected_slot = next(slot for slot in available_slots_with_numbers if slot['time'] == selected_time)
                                            slot_number = selected_slot['slot_number']  # Extract the slot number from the available slots


                                if selected_time and is_valid_phone(phone_number) and is_valid_email(email):
                                    # Step 7: Reschedule Appointment
                                    if st.button("Reschedule Appointment"):
                                        # Generate the Patient ID
                                        patient_id = generate_patient_id(
                                            appointments_data,
                                            email
                                        )

                                        booking_data = {
                                            "Patient ID": patient_id, 
                                            "Patient Name": patient_name,
                                            "Patient Name": patient_name,
                                            "Gender": gender,
                                            "Age": age,
                                            "Phone Number": phone_number,
                                            "Email": email,
                                            "Specialization": selected_specialization,
                                            "Doctor": selected_doctor,
                                            "Date": new_date,
                                            "Time": selected_time,
                                            "Slot Number": slot_number,
                                            "Specialization_ID": specialization_id,
                                            "Doctor_ID": doctor_id
                                        }

                                        # Save the rescheduled appointment
                                        save_booking(booking_data)

                                        # Create ICS calendar invite
                                        ics_content = create_calendar_invite(booking_data)

                                        # Send email notification with calendar invite
                                        email_subject = "Appointment Successfully Rescheduled"
                                        email_body = (
                                            f"Dear {booking_data['Patient Name']},\n\n"
                                            f"Your appointment has been successfully rescheduled:\n"
                                            f"Doctor: Dr. {booking_data['Doctor']}\n"
                                            f"Specialization: {booking_data['Specialization']}\n"
                                            f"Date: {booking_data['Date']}\n"
                                            f"Time: {booking_data['Time']}\n"
                                            f"Slot Number: {booking_data['Slot Number']}\n\n"
                                            f"Thank you for choosing our services!"
                                        )
                                        send_email_notification(booking_data['Email'], email_subject, email_body, ics_content)

                                        # Display success message
                                        st.success(
                                            f"Appointment successfully rescheduled!\n\n"
                                            f"**Patient Name:** {patient_name}\n"
                                            #f"**Gender:** {gender}\n"
                                            f"**Age:** {age}\n"
                                            f"**Contact Number:** {phone_number}\n"
                                            f"**Email:** {email}\n"
                                            f"**Doctor:** Dr. {selected_doctor}\n"
                                            f"**Specialization:** {selected_specialization}\n"
                                            f"**New Date:** {new_date}\n"
                                            f"**New Time:** {selected_time}\n"
                                            f"**Slot Number:** {slot_number}"
                                        )
                                        # Asking if the user needs further assistance
                                        st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": "Is there anything else I can assist you with?"
                                        })


                                        st.session_state.flow = None
                                        st.session_state.show_menu = False  # Hide the menu after booking
                                else:
                                    st.warning("Please ensure all details are valid and a time slot is selected.")
                            else:
                                st.warning(f"No doctors available for specialization: {selected_specialization}.")
                        else:
                            st.warning("Please select a specialization.")
                    else:
                         st.warning(f"No missed appointments found for {patient_email_to_reschedule}.") 

                # Go Back to Menu button
                if st.button("Go Back to Menu"):
                    st.session_state.flow = None
                    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you today?"}]
