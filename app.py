"""
RTI Response Summarization System
Main Streamlit Application

An RTI-aware semantic processing pipeline that structurally decomposes 
RTI responses and performs multi-level, action-oriented summarization.
"""

import streamlit as st
import io
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_TITLE, APP_SUBTITLE, COLORS, GEMINI_API_KEY, ENABLE_LOCAL_FALLBACK
from modules.preprocessing import preprocess_pipeline, get_text_stats
from modules.rti_semantic import extract_structured_response, get_response_summary
from modules.summarizer import (
    generate_ultra_short_summary, 
    generate_citizen_summary, 
    generate_technical_summary,
    test_connection,
    SummaryResult
)
from modules.fact_extractor import extract_fact_anchors, format_fact_anchors
from modules.actionability import generate_action_report
import time
from utils.helpers import export_to_text

# Page Configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# styling
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Summary card styling */
    .summary-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 5px solid;
        color: #1f2937 !important;
    }
    
    .summary-card * {
        color: #1f2937 !important;
    }
    
    .summary-card.ultra-short {
        border-left-color: #6366f1;
    }
    
    .summary-card.citizen {
        border-left-color: #10b981;
    }
    
    .summary-card.technical {
        border-left-color: #f59e0b;
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Sentence highlighting */
    .sentence-tag {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.25rem;
        font-size: 0.9rem;
    }
    
    .tag-informative {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #10b981;
    }
    
    .tag-denial {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #ef4444;
    }
    
    .tag-procedural {-[=]
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .tag-evasive {
        background-color: #ffedd5;
        color: #9a3412;
        border: 1px solid #f97316;
    }
    
    /* Action suggestion styling */
    .action-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        color: #1f2937 !important;
    }
    
    .action-card * {
        color: #1f2937 !important;
    }
    
    .action-high {
        border-left: 4px solid #ef4444;
    }
    
    .action-medium {
        border-left: 4px solid #f59e0b;
    }
    
    .action-low {
        border-left: 4px solid #10b981;
    }
    
    /* Stats box */
    .stats-container {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    .stat-box {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        min-width: 100px;
    }
    
    .stat-number {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1e40af;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #64748b;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown(f"""
    <div class="main-header">
        <h1>📋 {APP_TITLE}</h1>
        <p>{APP_SUBTITLE}</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with settings and info."""
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Enter your Google Gemini API key"
        )
        
        if api_key:
            if st.button("🔗 Test Connection"):
                with st.spinner("Testing..."):
                    if test_connection(api_key):
                        st.success("✅ Connected!")
                    else:
                        st.error("❌ Connection failed")
        
        st.divider()
        
        # Info section
        st.header("ℹ️ About")
        st.markdown("""
        This system analyzes RTI (Right to Information) responses and provides:
        
        - **Multi-level summaries** (ultra-short, citizen-friendly, technical)
        - **Response classification** (informative, denial, procedural, evasive)
        - **Action suggestions** based on response analysis
        """)
        
        st.divider()
        
        # Legend
        st.header("🎨 Color Legend")
        st.markdown("""
        <div class="sentence-tag tag-informative">🟢 Informative</div>
        <div class="sentence-tag tag-denial">🔴 Denial</div>
        <div class="sentence-tag tag-procedural">🟡 Procedural</div>
        <div class="sentence-tag tag-evasive">🟠 Evasive</div>
        """, unsafe_allow_html=True)
        
        return api_key


def render_input_section():
    """Render the input section with PDF upload and text input."""
    st.header("📥 Input RTI Response")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload an RTI response PDF document"
        )
    
    with col2:
        st.subheader("📝 Paste Text")
        pasted_text = st.text_area(
            "Or paste RTI response text here",
            height=200,
            placeholder="Paste your RTI response text here..."
        )
    
    return uploaded_file, pasted_text


def render_summary_card(title: str, icon: str, content: str, card_class: str):
    """Render a summary card."""
    st.markdown(f"""
    <div class="summary-card {card_class}">
        <div class="card-title">{icon} {title}</div>
        <div>{content}</div>
    </div>
    """, unsafe_allow_html=True)


def render_classified_sentences(structured_response):
    """Render classified sentences with color coding."""
    st.subheader("📊 Classified Sentences")
    
    tabs = st.tabs(["🟢 Informative", "🔴 Denied", "🟡 Procedural", "🟠 Evasive"])
    
    with tabs[0]:
        if structured_response.informative_sentences:
            for s in structured_response.informative_sentences:
                st.markdown(f'<div class="sentence-tag tag-informative">{s.text}</div>', 
                           unsafe_allow_html=True)
        else:
            st.info("No informative sentences found")
    
    with tabs[1]:
        if structured_response.denial_sentences:
            for s in structured_response.denial_sentences:
                st.markdown(f'<div class="sentence-tag tag-denial">{s.text}</div>', 
                           unsafe_allow_html=True)
        else:
            st.success("No denials found")
    
    with tabs[2]:
        if structured_response.procedural_sentences:
            for s in structured_response.procedural_sentences:
                st.markdown(f'<div class="sentence-tag tag-procedural">{s.text}</div>', 
                           unsafe_allow_html=True)
        else:
            st.info("No procedural statements found")
    
    with tabs[3]:
        if structured_response.evasive_sentences:
            for s in structured_response.evasive_sentences:
                st.markdown(f'<div class="sentence-tag tag-evasive">{s.text}</div>', 
                           unsafe_allow_html=True)
        else:
            st.success("No evasive responses found")


def render_action_suggestions(action_report):
    """Render action suggestions."""
    st.subheader("🎯 Suggested Actions")
    
    # Overall assessment
    assessment = action_report.get('overall_assessment', 'N/A')
    if 'SATISFACTORY' in assessment:
        st.success(f"**Assessment:** {assessment}")
    elif 'UNSATISFACTORY' in assessment or 'INADEQUATE' in assessment:
        st.error(f"**Assessment:** {assessment}")
    else:
        st.warning(f"**Assessment:** {assessment}")
    
    # Suggestions
    for suggestion in action_report.get('suggestions', []):
        priority = suggestion.get('priority', 'low')
        priority_class = f"action-{priority}"
        
        with st.container():
            st.markdown(f"""
            <div class="action-card {priority_class}">
                <strong>{suggestion.get('title', 'Action')}</strong>
                <p>{suggestion.get('description', '')}</p>
                {'<small>⏰ <em>Deadline: ' + suggestion.get('deadline', '') + '</em></small>' if suggestion.get('deadline') else ''}
                {'<br><small>📖 <em>Reference: ' + suggestion.get('reference', '') + '</em></small>' if suggestion.get('reference') else ''}
            </div>
            """, unsafe_allow_html=True)


def render_stats(stats: dict):
    """Render text statistics."""
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("Total Sentences", stats.get('total_sentences', 0))
    with cols[1]:
        st.metric("Informative", stats.get('informative_count', 0))
    with cols[2]:
        st.metric("Denied", stats.get('denial_count', 0))
    with cols[3]:
        st.metric("Evasive", stats.get('evasive_count', 0))


def main():
    """Main application function."""
    render_header()
    api_key = render_sidebar()
    
    uploaded_file, pasted_text = render_input_section()
    
    # Analyze button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("🔍 Analyze RTI Response", type="primary", use_container_width=True)
    
    if analyze_button:
        # Check for input
        if not uploaded_file and not pasted_text:
            st.error("Please upload a PDF or paste text to analyze.")
            return
        
        # Check for API key
        if not api_key:
            if ENABLE_LOCAL_FALLBACK:
                st.info("ℹ️ No API key provided. Local fallback summarizer will be used.")
            else:
                st.warning("⚠️ Gemini API key not provided. Summaries will not be generated.")
        
        # Clear previous summaries when re-analyzing
        for key in ['ultra_short', 'citizen_friendly', 'technical']:
            if key in st.session_state:
                del st.session_state[key]
        
        with st.spinner("Processing RTI response..."):
            try:
                # Step 1: Preprocessing
                st.info("📄 Extracting and cleaning text...")
                if uploaded_file:
                    text = preprocess_pipeline(uploaded_file.read(), is_pdf=True)
                else:
                    text = preprocess_pipeline(pasted_text, is_pdf=False)
                
                # Step 2: Semantic Processing (for UI/stats ONLY, not for summarization)
                st.info("🧠 Analyzing RTI-specific semantics...")
                structured_response = extract_structured_response(text)
                
                # Step 3: Extract Fact Anchors (for summarization)
                st.info("📌 Extracting key facts...")
                fact_anchors = extract_fact_anchors(text)
                
                # Step 4: Generate Action Report
                st.info("🎯 Generating action suggestions...")
                action_report = generate_action_report(structured_response)
                
                # Store ALL data in session state
                # NOTE: full_text is used for summarization (NOT classification-filtered text)
                st.session_state['full_text'] = text  # Full cleaned text for summarization
                st.session_state['fact_anchors'] = fact_anchors  # Fact anchors
                st.session_state['api_key'] = api_key
                st.session_state['structured_response'] = structured_response
                st.session_state['action_report'] = action_report
                st.session_state['original_text'] = text
                st.session_state['analysis_done'] = True
                
                st.success("✅ Analysis complete!")
                
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
                return
    
    # Display results if analysis has been done (persists across button clicks)
    if st.session_state.get('analysis_done', False):
        st.divider()
        
        # Retrieve from session state
        structured_response = st.session_state['structured_response']
        action_report = st.session_state['action_report']
        original_text = st.session_state['original_text']
        stored_api_key = st.session_state.get('api_key', api_key)
        
        # Display Results
        st.header("📊 Analysis Results")
        
        # Statistics
        stats = structured_response.get_stats()
        render_stats(stats)
        
        st.divider()
        
        # Summaries Section with Selectable Buttons
        # Get full text and fact anchors for summarization
        full_text = st.session_state.get('full_text', original_text)
        fact_anchors = st.session_state.get('fact_anchors', [])
        
        st.header("📝 Summaries")
        
        # Show fact anchors in expander
        with st.expander("📌 View Extracted Fact Anchors"):
            if fact_anchors:
                for i, anchor in enumerate(fact_anchors, 1):
                    st.markdown(f"**{i}.** {anchor}")
            else:
                st.info("No fact anchors extracted.")
        
        st.caption("💡 Click a button to generate that summary type. Uses fact-anchored prompting for content-aware summaries.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⚡ Ultra-Short", use_container_width=True):
                with st.spinner("Generating ultra-short summary..."):
                    time.sleep(1)  # Small delay
                    # Use FULL TEXT + fact anchors (NOT classification-filtered text)
                    result = generate_ultra_short_summary(full_text, stored_api_key, fact_anchors)
                    st.session_state['current_summary_result'] = result
                    st.session_state['current_summary_type'] = 'ultra_short'
                    st.rerun()
        
        with col2:
            if st.button("👤 Citizen-Friendly", use_container_width=True):
                with st.spinner("Generating citizen-friendly summary..."):
                    time.sleep(1)
                    result = generate_citizen_summary(full_text, stored_api_key, fact_anchors)
                    st.session_state['current_summary_result'] = result
                    st.session_state['current_summary_type'] = 'citizen_friendly'
                    st.rerun()
        
        with col3:
            if st.button("⚖️ Technical/Legal", use_container_width=True):
                with st.spinner("Generating technical summary..."):
                    time.sleep(1)
                    result = generate_technical_summary(full_text, stored_api_key, fact_anchors)
                    st.session_state['current_summary_result'] = result
                    st.session_state['current_summary_type'] = 'technical'
                    st.rerun()
            
        # Display only the currently selected summary with source badge
        if 'current_summary_result' in st.session_state and 'current_summary_type' in st.session_state:
            summary_type = st.session_state['current_summary_type']
            summary_result = st.session_state['current_summary_result']
            
            # Handle both old string format and new SummaryResult format
            if isinstance(summary_result, SummaryResult):
                summary_content = summary_result.text
                source = summary_result.source
            else:
                summary_content = str(summary_result)
                source = "unknown"
            
            # Show source badge
            if source == "gemini":
                st.success("🌐 **Powered by Gemini API**")
            elif source == "local_fallback":
                st.warning("💻 **Generated by Local Fallback** (Gemini API unavailable)")
            elif source == "error":
                st.error("⚠️ **Error occurred during generation**")
            
            if summary_type == 'ultra_short':
                render_summary_card(
                    "Ultra-Short Summary",
                    "⚡",
                    summary_content,
                    "ultra-short"
                )
            elif summary_type == 'citizen_friendly':
                render_summary_card(
                    "Citizen-Friendly Summary",
                    "👤",
                    summary_content,
                    "citizen"
                )
            elif summary_type == 'technical':
                render_summary_card(
                    "Technical/Legal Summary",
                    "⚖️",
                    summary_content,
                    "technical"
                )
        
        st.divider()
        
        # Classified Sentences
        render_classified_sentences(structured_response)
        
        st.divider()
        
        # Action Suggestions
        render_action_suggestions(action_report)
        
        st.divider()
        
        # Original Text (Expandable)
        with st.expander("📜 View Original Text"):
            st.text(original_text)
        
        # Download Button
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Build export data based on current summary
            current_type = st.session_state.get('current_summary_type', '')
            current_result = st.session_state.get('current_summary_result', None)
            
            # Extract text from SummaryResult or use as string
            if current_result:
                if isinstance(current_result, SummaryResult):
                    current_content = current_result.text
                else:
                    current_content = str(current_result)
            else:
                current_content = 'N/A'
            
            export_data = {
                'ultra_short': current_content if current_type == 'ultra_short' else 'N/A',
                'citizen_friendly': current_content if current_type == 'citizen_friendly' else 'N/A',
                'technical': current_content if current_type == 'technical' else 'N/A',
                'actions': [s.get('title', '') + ': ' + s.get('description', '') 
                           for s in action_report.get('suggestions', [])]
            }
            export_text = export_to_text(export_data)
            
            st.download_button(
                label="📥 Download Summary Report",
                data=export_text,
                file_name="rti_summary_report.txt",
                mime="text/plain",
                use_container_width=True
            )


if __name__ == "__main__":
    main()

