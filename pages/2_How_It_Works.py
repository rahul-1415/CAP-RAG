import streamlit as st

from components.navigation import render_top_nav
from components.theme import apply_theme_styles, init_theme_state, render_dark_mode_slider

st.set_page_config(page_title="How It Works", page_icon=":material/schema:", layout="wide")

init_theme_state(default_dark_mode=False)
apply_theme_styles()
render_dark_mode_slider()
render_top_nav(active_page="how_it_works")

st.title("How It Works")
st.caption("From user query to policy-grounded answer.")

st.subheader("System Flow")
st.markdown(
    """
1. **User asks a question** in the chat interface.
2. **Retriever searches policy chunks** in Chroma using embedding similarity + MMR.
3. **Top evidence is assembled** into a context window (char-limited).
4. **LLM generates response** using only retrieved context.
5. **Evidence is shown** so users can inspect source snippets.
"""
)

st.subheader("Technical Components")
st.markdown(
    """
- **Embedding model**: `BAAI/bge-small-en-v1.5`
- **Vector DB**: Chroma (persistent local directory)
- **Retriever mode**: MMR (`k=5`, diversified results)
- **Generation models**: Groq-hosted Llama variants
- **UI**: Streamlit chat interface with multi-session history
"""
)

st.subheader("Use-Case Examples")
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "City Climate Office",
        "Transport Planning",
        "Grant / Funding Prep",
        "Academic Research",
    ]
)

with tab1:
    st.markdown(
        """
**Goal**: Identify actions to reduce building emissions in cities.  
**Example prompt**: "What building retrofit policies are most commonly recommended in C40 case studies?"  
**What the app returns**: A summarized set of retrofit approaches grounded in retrieved policy documents.
"""
    )

with tab2:
    st.markdown(
        """
**Goal**: Plan mobility decarbonization options.  
**Example prompt**: "What policies support electric bus adoption and low-emission zones?"  
**What the app returns**: Policy levers, implementation notes, and evidence excerpts from relevant documents.
"""
    )

with tab3:
    st.markdown(
        """
**Goal**: Draft evidence-backed proposals for climate funding.  
**Example prompt**: "Give policy examples for urban heat adaptation that can justify funding requests."  
**What the app returns**: Context-grounded bullet points and references usable in grant narratives.
"""
    )

with tab4:
    st.markdown(
        """
**Goal**: Compare policy patterns across themes.  
**Example prompt**: "Compare adaptation vs mitigation policy recommendations in the dataset."  
**What the app returns**: A structured comparison based on retrieved passages, not generic model knowledge.
"""
    )

st.subheader("Prompt Patterns That Work Well")
st.code(
    """- "Summarize policy recommendations for [topic] in [region/city context]."
- "Compare approaches for [policy A] vs [policy B] using source evidence."
- "List implementation steps, barriers, and enablers for [climate action]."
- "What data points from C40 examples can support a proposal on [theme]?" """
)
