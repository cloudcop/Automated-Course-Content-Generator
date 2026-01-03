import streamlit as st
import os
import json
import base64
import time
from dotenv import load_dotenv
from openai import OpenAI
from utils import generate_pdf, load_chat_history, save_chat_history

# Import Prompts
from prompts.tabler_prompt import TABLER_PROMPT
from prompts.coursify_prompt import generate_coursify_prompt
from prompts.quizzy_prompt import QUIZZY_PROMPT
from prompts.dictator_prompt import DICTATOR_PROMPT

# Config
st.set_page_config(
    page_title="Automated Course Content Generator",
    page_icon=":robot:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_dotenv()

st.title("Automated Course Content Generator 🤖")

# --- OpenAI Setup ---
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    # If no env var, try getting it from sidebar input for user convenience
    with st.sidebar:
        api_key = st.text_input("Enter OpenAI API Key", type="password")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            st.success("API Key loaded!")

if not api_key:
    st.warning("⚠️ Please provide an OpenAI API Key in the sidebar or .env file to function.")
    st.stop()

client = OpenAI(api_key=api_key)

def get_completion(prompt, model="gpt-3.5-turbo"):
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

# --- Main Logic ---

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

with st.sidebar:
    if st.button("Delete Chat History"):
        st.session_state.messages = []
        save_chat_history([])

col1, col2 = st.columns([3.0, 7.0])

with col1:
    st.header("Course Details 📋")
    course_name = st.text_input("Course Name", value="Intro to Python")
    target_audience_edu_level = st.selectbox("Target Audience Edu Level", ["Beginner", "Intermediate", "Advanced"])
    difficulty_level = st.radio("Course Difficulty Level", ["Easy", "Medium", "Hard"])
    num_modules = st.slider("No. of Modules", 1, 10, 3)
    course_duration = st.text_input("Course Duration", value="2 Weeks")
    course_credit = st.text_input("Course Credit", value="1")

    # State management
    st.session_state.update({
        "course_name": course_name,
        "target_audience_edu_level": target_audience_edu_level,
        "difficulty_level": difficulty_level,
        "num_modules": num_modules
    })

    b1, b2 = st.columns([1, 0.8])
    with b1:
        generate_btn = st.button("Generate Course Outline")
    with b2:
        if st.button("Reset"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

with col2:
    st.header("Generated Content 📝")

    # 1. Generate Outline
    if generate_btn:
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
            outline = get_completion(full_prompt)
            
            if outline:
                st.session_state['course_outline'] = outline
                st.session_state['buttons_visible'] = True
                st.success("Outline Generated!")

    # 2. Display Outline & Actions
    if 'course_outline' in st.session_state:
        with st.expander("Course Outline", expanded=True):
            st.write(st.session_state['course_outline'])
        
        if st.session_state.get('buttons_visible'):
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("Generate Full Course"):
                    st.session_state['complete_course'] = True
            with c2:
                if st.button("Modify Outline"):
                    st.info("Edit functionality coming soon. Proceeding with current outline.")

    # 3. Generate Full Course
    if st.session_state.get('complete_course'):
        if 'module_dict' not in st.session_state:
            with st.spinner("Parsing Outline Structure..."):
                dict_prompt = DICTATOR_PROMPT + "\n\nCourse Outline:\n" + st.session_state['course_outline']
                json_str = get_completion(dict_prompt, model="gpt-3.5-turbo") # Use cheaper model for parsing
                try:
                    # sometimes the model returns markdown code block
                    json_str = json_str.replace("```json", "").replace("```", "")
                    st.session_state['module_dict'] = json.loads(json_str)
                except Exception as e:
                    st.error(f"Failed to parse outline: {e}")
                    st.stop()

        module_data = st.session_state['module_dict']
        full_text_accumulator = ""

        # Progress bar
        total_items = sum(len(lessons) for lessons in module_data.values()) + len(module_data)
        progress_bar = st.progress(0)
        completed_items = 0

        for module, lessons in module_data.items():
            module_content = f"# {module}\n\n"
            
            # Generate Lessons
            for lesson in lessons:
                with st.spinner(f"Writing {lesson}..."):
                    lesson_prompt = generate_coursify_prompt(lesson, module, course_name)
                    lesson_content = get_completion(lesson_prompt, model="gpt-4-turbo-preview") # Use better model for content
                    if not lesson_content: lesson_content = "Error generating content."
                    
                    module_content += f"{lesson_content}\n\n---\n\n"
                    
                    with st.expander(f"📖 {lesson}"):
                        st.markdown(lesson_content)
                    
                    completed_items += 1
                    progress_bar.progress(completed_items / total_items)

            # Generate Quiz
            with st.spinner(f"Creating Quiz for {module}..."):
                quiz_prompt = QUIZZY_PROMPT + f"\n\nModule Content:\n{module_content}"
                quiz_content = get_completion(quiz_prompt)
                if not quiz_content: quiz_content = "Error generating quiz."
                
                module_content += f"## Quiz\n{quiz_content}\n\n"
                
                with st.expander(f"🧩 Quiz for {module}"):
                    st.markdown(quiz_content)
                
                completed_items += 1
                progress_bar.progress(completed_items / total_items)

            full_text_accumulator += module_content + "\n\n"

        # PDF Generation
        if full_text_accumulator:
            pdf = generate_pdf(full_text_accumulator, "course_content.pdf")
            if pdf:
                try:
                    b64 = base64.b64encode(pdf.output(dest="S").encode('latin1')).decode()
                    st.success("Course Generation Complete!")
                    st.download_button(
                        label="Download PDF Course",
                        data=b64,
                        file_name=f"{course_name.replace(' ', '_')}_Course.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                     st.error(f"PDF Download Error: {e}")