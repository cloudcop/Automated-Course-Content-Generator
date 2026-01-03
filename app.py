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
    page_title="ACCG - AI Course Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for UI enhancements
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        color: #2e86c1;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    .stProgress .st-bo {
        background-color: #2e86c1;
    }
</style>
""", unsafe_allow_html=True)

# Try importing OpenAI, handle gracefully if missing
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# --- UI Header ---
st.title("🎓 Automated Course Content Generator")
st.markdown("### Empower your teaching with AI-driven course creation")
st.divider()

# --- UI Layout ---

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Settings")
    st.info("Configure your AI access below.")
    api_key_input = st.text_input("OpenAI API Key", type="password", help="Required to generate real content.")
    
    st.divider()
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        save_chat_history([])
        st.rerun()
    
    st.markdown("---")
    st.caption("v1.0.0 | Built with Streamlit & OpenAI")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# Main Layout
col1, col2 = st.columns([4, 8], gap="large")

# Left Column: Inputs
with col1:
    st.subheader("📋 Course Details")
    
    with st.container(border=True):
        course_name = st.text_input("Course Name", value="Intro to Python")
        target_audience_edu_level = st.selectbox("Target Audience Level", ["Beginner", "Intermediate", "Advanced"])
        difficulty_level = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Hard"])
        num_modules = st.slider("Number of Modules", 1, 10, 3)
        
        c_dur, c_cred = st.columns(2)
        with c_dur:
            course_duration = st.text_input("Duration", value="2 Weeks")
        with c_cred:
            course_credit = st.text_input("Credit", value="1")

    # Save to session state
    st.session_state.update({
        "course_name": course_name,
        "target_audience_edu_level": target_audience_edu_level,
        "difficulty_level": difficulty_level,
        "num_modules": num_modules
    })

    st.write("") # Spacer
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        generate_btn = st.button("✨ Generate Outline", type="primary")
    with btn_col2:
        if st.button("🔄 Reset App"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Right Column: Results
with col2:
    st.subheader("📝 Generated Content")
    
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
                    st.success("Outline Generated Successfully!")

    # 2. Display Outline & Actions
    if 'course_outline' in st.session_state:
        with st.expander("📂 View Course Outline", expanded=True):
            st.markdown(st.session_state['course_outline'])
        
        st.write("")
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("🚀 Generate Full Course", type="primary"):
                st.session_state['complete_course'] = True
        with c2:
            st.info("Tip: Review the outline above before generating the full content.")

    # 3. Generate Full Course Action
    if st.session_state.get('complete_course'):
        client = get_api_client()
        if not client:
             st.error("API Key lost. Please re-enter in sidebar.")
        else:
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
                        st.write(json_str) # Debug info
                        
            if 'module_dict' in st.session_state:
                module_data = st.session_state['module_dict']
                full_text_accumulator = ""

                # Progress bar
                total_items = sum(len(lessons) for lessons in module_data.values()) + len(module_data)
                progress_bar = st.progress(0)
                status_text = st.empty()
                completed_items = 0

                # Placeholder for live content updates
                content_placeholder = st.empty()

                for module, lessons in module_data.items():
                    module_content = f"# {module}\n\n"
                    
                    # Generate Lessons
                    for lesson in lessons:
                        status_text.text(f"Writing: {lesson}...")
                        lesson_prompt = generate_coursify_prompt(lesson, module, course_name)
                        # Fallback to 3.5 if 4 is too expensive or unavailable for user
                        lesson_content = get_completion(client, lesson_prompt, model="gpt-3.5-turbo") 
                        if not lesson_content: lesson_content = "Error generating content."
                        
                        module_content += f"{lesson_content}\n\n---\n\n"
                        
                        completed_items += 1
                        progress_bar.progress(min(completed_items / total_items, 1.0))

                    # Generate Quiz
                    status_text.text(f"Creating Quiz for {module}...")
                    quiz_prompt = QUIZZY_PROMPT + f"\n\nModule Content:\n{module_content}"
                    quiz_content = get_completion(client, quiz_prompt)
                    if not quiz_content: quiz_content = "Error generating quiz."
                    
                    module_content += f"## Quiz\n{quiz_content}\n\n"
                    
                    completed_items += 1
                    progress_bar.progress(min(completed_items / total_items, 1.0))

                    full_text_accumulator += module_content + "\n\n"
                    
                    # Show completed module in expander
                    with st.expander(f"✅ {module} (Complete)"):
                        st.markdown(module_content)

                status_text.text("Generation Complete!")
                content_placeholder.empty()

                # PDF Generation
                if full_text_accumulator:
                    pdf = generate_pdf(full_text_accumulator, "course_content.pdf")
                    if pdf:
                        try:
                            b64 = base64.b64encode(pdf.output(dest="S").encode('latin1')).decode()
                            st.balloons()
                            st.success("🎉 Course Generation Complete!")
                            st.download_button(
                                label="📥 Download PDF Course",
                                data=b64,
                                file_name=f"{course_name.replace(' ', '_')}_Course.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"PDF Download Error: {e}")