import streamlit as st
import os
import json
import base64
import time
from utils import generate_pdf, load_chat_history, save_chat_history

# Import Prompts
from prompts.tabler_prompt import TABLER_PROMPT
from prompts.coursify_prompt import generate_coursify_prompt
from prompts.quizzy_prompt import QUIZZY_PROMPT
from prompts.dictator_prompt import DICTATOR_PROMPT

# Config MUST be the first command
st.set_page_config(
    page_title="Automated Course Content Generator",
    page_icon=":robot:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Try importing OpenAI, handle gracefully if missing
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

st.title("Automated Course Content Generator 🤖")

# --- UI Layout ---

# Sidebar for controls
with st.sidebar:
    st.header("Settings")
    api_key_input = st.text_input("OpenAI API Key", type="password", help="Required to generate real content.")
    
    st.divider()
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        save_chat_history([])
        st.rerun()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# Main Layout
col1, col2 = st.columns([3.0, 7.0])

# Left Column: Inputs
with col1:
    st.header("Course Details 📋")
    
    with st.container(border=True):
        course_name = st.text_input("Course Name", value="Intro to Python")
        target_audience_edu_level = st.selectbox("Target Audience Edu Level", ["Beginner", "Intermediate", "Advanced"])
        difficulty_level = st.radio("Course Difficulty Level", ["Easy", "Medium", "Hard"], horizontal=True)
        num_modules = st.slider("No. of Modules", 1, 10, 3)
        course_duration = st.text_input("Course Duration", value="2 Weeks")
        course_credit = st.text_input("Course Credit", value="1")

    # Save to session state
    st.session_state.update({
        "course_name": course_name,
        "target_audience_edu_level": target_audience_edu_level,
        "difficulty_level": difficulty_level,
        "num_modules": num_modules
    })

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        generate_btn = st.button("Generate Outline", type="primary", use_container_width=True)
    with btn_col2:
        if st.button("Reset App", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Right Column: Results
with col2:
    st.header("Generated Content 📝")
    
    # --- Logic Helpers ---
    def get_api_client():
        # Check env var first, then sidebar input
        key = os.getenv("OPENAI_API_KEY") or api_key_input
        if not key:
            return None
        return OpenAI(api_key=key)

    def get_completion(client, prompt, model="gpt-3.5-turbo"):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
            return None

    # 1. Generate Outline Action
    if generate_btn:
        client = get_api_client()
        if not HAS_OPENAI:
             st.error("OpenAI library is missing. Please rebuild the app.")
        elif not client:
            st.warning("⚠️ Please enter an OpenAI API Key in the sidebar to generate content.")
        else:
            user_input = f"""
            Topic: {course_name}
            Audience Level: {target_audience_edu_level}
            Difficulty: {difficulty_level}
            Number of Modules: {num_modules}
            Duration: {course_duration}
            Credit: {course_credit}
            """
            
            with st.spinner("Generating Outline..."):
                full_prompt = TABLER_PROMPT + "\n\nUser Input Topic: " + user_input
                outline = get_completion(client, full_prompt)
                
                if outline:
                    st.session_state['course_outline'] = outline
                    st.success("Outline Generated!")

    # 2. Display Outline & Actions
    if 'course_outline' in st.session_state:
        with st.expander("Course Outline", expanded=True):
            st.write(st.session_state['course_outline'])
        
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("Generate Full Course", type="primary"):
                st.session_state['complete_course'] = True
        with c2:
            st.caption("Modifying outline feature coming soon.")

    # 3. Generate Full Course Action
    if st.session_state.get('complete_course'):
        client = get_api_client()
        if not client:
             st.error("API Key lost. Please re-enter in sidebar.")
             st.stop()

        if 'module_dict' not in st.session_state:
            with st.spinner("Parsing Outline Structure..."):
                dict_prompt = DICTATOR_PROMPT + "\n\nCourse Outline:\n" + st.session_state['course_outline']
                json_str = get_completion(client, dict_prompt, model="gpt-3.5-turbo")
                try:
                    if json_str:
                        json_str = json_str.replace("```json", "").replace("```", "")
                        st.session_state['module_dict'] = json.loads(json_str)
                except Exception as e:
                    st.error(f"Failed to parse outline: {e}")
                    st.stop()

        if 'module_dict' in st.session_state:
            module_data = st.session_state['module_dict']
            full_text_accumulator = ""

            # Progress bar
            total_items = sum(len(lessons) for lessons in module_data.values()) + len(module_data)
            progress_bar = st.progress(0)
            completed_items = 0

            # Placeholder for live content updates
            content_placeholder = st.empty()

            for module, lessons in module_data.items():
                module_content = f"# {module}\n\n"
                
                # Generate Lessons
                for lesson in lessons:
                    with st.spinner(f"Writing {lesson}..."):
                        lesson_prompt = generate_coursify_prompt(lesson, module, course_name)
                        # Fallback to 3.5 if 4 is too expensive or unavailable for user
                        lesson_content = get_completion(client, lesson_prompt, model="gpt-3.5-turbo") 
                        if not lesson_content: lesson_content = "Error generating content."
                        
                        module_content += f"{lesson_content}\n\n---\n\n"
                        
                        # Update UI live
                        with content_placeholder.container():
                            st.markdown(f"### Currently writing: {lesson}")
                        
                        completed_items += 1
                        progress_bar.progress(completed_items / total_items)

                # Generate Quiz
                with st.spinner(f"Creating Quiz for {module}..."):
                    quiz_prompt = QUIZZY_PROMPT + f"\n\nModule Content:\n{module_content}"
                    quiz_content = get_completion(client, quiz_prompt)
                    if not quiz_content: quiz_content = "Error generating quiz."
                    
                    module_content += f"## Quiz\n{quiz_content}\n\n"
                    
                    completed_items += 1
                    progress_bar.progress(completed_items / total_items)

                full_text_accumulator += module_content + "\n\n"
                
                # Show completed module in expander
                with st.expander(f"✅ {module} (Complete)"):
                    st.markdown(module_content)

            content_placeholder.empty()

            # PDF Generation
            if full_text_accumulator:
                pdf = generate_pdf(full_text_accumulator, "course_content.pdf")
                if pdf:
                    try:
                        b64 = base64.b64encode(pdf.output(dest="S").encode('latin1')).decode()
                        st.success("🎉 Course Generation Complete!")
                        st.download_button(
                            label="Download PDF Course",
                            data=b64,
                            file_name=f"{course_name.replace(' ', '_')}_Course.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"PDF Download Error: {e}")