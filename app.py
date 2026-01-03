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
    page_title="AI Course Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .main-header {
        font-size: 2.5rem;
        color: #4B4B4B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
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

# --- Header ---
st.markdown('<div class="main-header">Automated Course Content Generator 🎓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Empower your teaching with AI-driven course creation</div>', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key Handling
    env_key = os.getenv("OPENAI_API_KEY")
    api_key_input = st.text_input(
        "OpenAI API Key", 
        type="password", 
        value=env_key if env_key else "",
        help="Required to generate real content. Skips if found in .env"
    )
    
    st.info("💡 **Tip**: Add your API key to a `.env` file to skip this step.")
    
    st.divider()
    
    st.subheader("History Control")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        save_chat_history([])
        st.session_state.clear()
        st.rerun()

# Initialize session state for data persistence
if "course_outline" not in st.session_state:
    st.session_state["course_outline"] = None
if "module_dict" not in st.session_state:
    st.session_state["module_dict"] = None

# --- Logic Helpers ---
def get_api_client():
    key = api_key_input or os.getenv("OPENAI_API_KEY")
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
        st.error(f"OpenAI API Error: {e}")
        return None

# --- Main Layout ---
tab1, tab2, tab3 = st.tabs(["1️⃣ Course Configuration", "2️⃣ Outline Review", "3️⃣ Final Content"])

# TAB 1: Configuration
with tab1:
    col_input, col_info = st.columns([1, 1])
    
    with col_input:
        st.subheader("Define Your Course")
        with st.form("course_config_form"):
            course_name = st.text_input("Course Name", value="Introduction to Python Programming")
            target_audience = st.selectbox("Target Audience", ["Beginner", "Intermediate", "Advanced", "Professional"])
            difficulty = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Hard", "Expert"])
            
            c1, c2 = st.columns(2)
            with c1:
                num_modules = st.number_input("Number of Modules", min_value=1, max_value=10, value=3)
            with c2:
                course_duration = st.text_input("Duration", value="4 Weeks")
                
            course_credit = st.text_input("Course Credit (optional)", value="2 Credits")
            
            submitted = st.form_submit_button("✨ Generate Outline", type="primary")

    with col_info:
        st.info("### How it works\n1. **Define**: Enter the topic and parameters for your course.\n2. **Generate**: AI creates a structured outline based on Bloom's Taxonomy.\n3. **Review**: Check the outline and proceed to generate full lesson content.\n4. **Export**: Download the result as a PDF.")
        if not HAS_OPENAI:
            st.error("❌ OpenAI library not found. Please rebuild the app.")
        elif not get_api_client():
            st.warning("⚠️ Please provide an OpenAI API Key in the sidebar to proceed.")

    if submitted:
        client = get_api_client()
        if client:
            user_input = f"""
            Topic: {course_name}
            Audience: {target_audience}
            Difficulty: {difficulty}
            Modules: {num_modules}
            Duration: {course_duration}
            Credit: {course_credit}
            """
            
            # Save configs to state
            st.session_state.update({
                "course_name": course_name,
                "target_audience": target_audience
            })
            
            with st.spinner("🧠 AI is brainstorming your course outline..."):
                full_prompt = TABLER_PROMPT + "\n\nUser Input Topic: " + user_input
                outline = get_completion(client, full_prompt)
                
                if outline:
                    st.session_state['course_outline'] = outline
                    st.success("Outline generated! Go to the 'Outline Review' tab.")
                    time.sleep(1)
                    st.rerun()

# TAB 2: Outline Review
with tab2:
    if st.session_state['course_outline']:
        st.subheader("📝 Review Course Outline")
        
        with st.container(border=True):
            st.markdown(st.session_state['course_outline'])
        
        st.write("---")
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("🚀 Approve Outline & Generate Full Content", type="primary"):
                st.session_state['generate_full'] = True
                st.rerun()
    else:
        st.info("👈 Please generate an outline in the first tab.")

# TAB 3: Full Content Generation
with tab3:
    if st.session_state.get('generate_full'):
        client = get_api_client()
        
        # 1. Parse Outline to JSON
        if not st.session_state.get('module_dict'):
            with st.status("🔍 Analyzing structure...", expanded=True) as status:
                st.write("Parsing outline into modules...")
                dict_prompt = DICTATOR_PROMPT + "\n\nCourse Outline:\n" + st.session_state['course_outline']
                json_str = get_completion(client, dict_prompt)
                
                try:
                    if json_str:
                        # Clean cleanup of potential markdown code blocks
                        json_str = json_str.replace("```json", "").replace("```", "").strip()
                        st.session_state['module_dict'] = json.loads(json_str)
                        status.update(label="Structure analyzed!", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="Error parsing outline", state="error")
                    st.error(f"Parsing Error: {e}")
                    st.stop()

        # 2. Generate Content
        if st.session_state.get('module_dict'):
            module_data = st.session_state['module_dict']
            full_text_accumulator = ""
            
            # Calculate total steps for progress
            total_lessons = sum(len(lessons) for lessons in module_data.values())
            total_quizzes = len(module_data)
            total_steps = total_lessons + total_quizzes
            current_step = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Container for results
            results_container = st.container()

            # We iterate and generate, accumulating text
            # Note: In a real app, we might want to cache individual lessons to avoid re-generating on rerun
            # For now, we generate everything in one go if it's not already in a "final_content" state variable.
            
            if "final_content" not in st.session_state:
                
                for module, lessons in module_data.items():
                    module_text = f"# {module}\n\n"
                    
                    # Lessons
                    for lesson in lessons:
                        status_text.markdown(f"**Writing:** {lesson}...")
                        lesson_prompt = generate_coursify_prompt(lesson, module, st.session_state.get("course_name", "Course"))
                        lesson_content = get_completion(client, lesson_prompt) or "Error generating content."
                        module_text += f"{lesson_content}\n\n---\n\n"
                        
                        current_step += 1
                        progress_bar.progress(min(current_step / total_steps, 0.99))
                    
                    # Quiz
                    status_text.markdown(f"**Generating Quiz for:** {module}...")
                    quiz_prompt = QUIZZY_PROMPT + f"\n\nModule Content:\n{module_text}"
                    quiz_content = get_completion(client, quiz_prompt) or "Error generating quiz."
                    module_text += f"## 🧩 Quiz Questions\n{quiz_content}\n\n"
                    
                    current_step += 1
                    progress_bar.progress(min(current_step / total_steps, 0.99))
                    
                    full_text_accumulator += module_text + "\n\n"
                
                st.session_state["final_content"] = full_text_accumulator
                progress_bar.progress(1.0)
                status_text.success("🎉 All content generated successfully!")
            
            # Display Final Result
            with results_container:
                st.subheader("Course Content Preview")
                with st.expander("📄 View Full Content", expanded=False):
                    st.markdown(st.session_state["final_content"])
                
                # PDF Generation
                if st.session_state.get("final_content"):
                    pdf = generate_pdf(st.session_state["final_content"], "course.pdf")
                    if pdf:
                        try:
                            pdf_bytes = pdf.output(dest="S").encode("latin-1")
                            b64 = base64.b64encode(pdf_bytes).decode()
                            
                            st.download_button(
                                label="📥 Download Course PDF",
                                data=pdf_bytes,
                                file_name="Course_Content.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"PDF encoding error: {e}")
    else:
         st.info("👈 Approve the outline in the previous tab to start content generation.")