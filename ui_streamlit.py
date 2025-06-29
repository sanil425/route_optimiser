import streamlit as st
import streamlit.components.v1 as components
from vrptw import run_vrptw

st.set_page_config(page_title="Route Optimiser", layout="centered")

st.title("🚚 Vehicle Routing with Time Windows")
st.markdown("Please enter your day's plan and we will compute the best route for you.")

# User instruction input box
user_instruction = st.text_area("Enter your plans:", height=250)

# Button to generate route
if st.button("Generate Optimised Route"):
    if not user_instruction.strip():
        st.warning("⚠️ Please enter your daily plans first.")
    else:
        with st.spinner("Generating your optimised route..."):
            try:
                map_file, summary, trip_summary, explanation = run_vrptw(user_instruction)
                st.success("✅ Route generated successfully!")

                # Trip Summary Section
                st.markdown("### 🧭 Trip Summary")
                st.markdown(f"""
                - **Total Stops**: {trip_summary["total_stops"]}
                - **Total Distance**: {trip_summary["total_distance"]:.1f} km
                - **Total Travel Time**: {trip_summary["total_travel_time"]:.0f} min
                - **Time Spent at Stops**: {trip_summary["total_stop_time"]:.0f} min
                - **Return to Origin**: {"Yes" if trip_summary["return_to_start"] else "No"}

                **Departure**: {trip_summary["start_time"]}  
                **Final Arrival**: {trip_summary["end_time"]}
                """)

                # GPT Text Summary
                st.markdown("### 📝 Detailed Schedule")
                st.text(summary)

                # Show route map
                st.markdown("### 🗺️ Route Map")
                with open(map_file, 'r', encoding='utf-8') as f:
                    html_string = f.read()
                    components.html(html_string, height=600, scrolling=True)

                # Route Logic Explanation
                st.markdown("### 🤖 Why this route?")
                st.info(explanation)


            except Exception as e:
                st.error(f"❌ Error while generating route: {e}")
