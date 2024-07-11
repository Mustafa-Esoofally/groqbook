import streamlit as st
from groq import Groq
import json
import os
from io import BytesIO
from markdown import markdown
from weasyprint import HTML, CSS
from dotenv import load_dotenv
import uuid
from urllib.parse import quote, unquote

# load .env file to environment
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)

if "api_key" not in st.session_state:
    st.session_state.api_key = GROQ_API_KEY

if "groq" not in st.session_state:
    if GROQ_API_KEY:
        st.session_state.groq = Groq()


class GenerationStatistics:
    def __init__(
        self,
        input_time=0,
        output_time=0,
        input_tokens=0,
        output_tokens=0,
        total_time=0,
        model_name="llama3-8b-8192",
    ):
        self.input_time = input_time
        self.output_time = output_time
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_time = (
            total_time  # Sum of queue, prompt (input), and completion (output) times
        )
        self.model_name = model_name

    def get_input_speed(self):
        """
        Tokens per second calculation for input
        """
        if self.input_time != 0:
            return self.input_tokens / self.input_time
        else:
            return 0

    def get_output_speed(self):
        """
        Tokens per second calculation for output
        """
        if self.output_time != 0:
            return self.output_tokens / self.output_time
        else:
            return 0

    def add(self, other):
        """
        Add statistics from another GenerationStatistics object to this one.
        """
        if not isinstance(other, GenerationStatistics):
            raise TypeError("Can only add GenerationStatistics objects")

        self.input_time += other.input_time
        self.output_time += other.output_time
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_time += other.total_time

    def __str__(self):
        return (
            f"\n## {self.get_output_speed():.2f} T/s ⚡\nRound trip time: {self.total_time:.2f}s  Model: {self.model_name}\n\n"
            f"| Metric          | Input          | Output          | Total          |\n"
            f"|-----------------|----------------|-----------------|----------------|\n"
            f"| Speed (T/s)     | {self.get_input_speed():.2f}            | {self.get_output_speed():.2f}            | {(self.input_tokens + self.output_tokens) / self.total_time if self.total_time != 0 else 0:.2f}            |\n"
            f"| Tokens          | {self.input_tokens}            | {self.output_tokens}            | {self.input_tokens + self.output_tokens}            |\n"
            f"| Inference Time (s) | {self.input_time:.2f}            | {self.output_time:.2f}            | {self.total_time:.2f}            |"
        )


class Book:
    def __init__(self, book_title, structure):
        self.book_title = book_title
        self.structure = structure
        # self.contents = {title: "" for title in self.flatten_structure(structure)}
        # self.placeholders = {title: st.empty() for title in self.flatten_structure(structure)}
        self.contents = self.initialize_contents(structure)
        st.markdown(f"# {self.book_title}")
        # st.markdown("## Generating the following:")
        # toc_columns = st.columns(4)
        # self.display_toc(self.structure, toc_columns)
        # st.markdown("---")

    
    def flatten_structure(self, structure, prefix=""):
        sections = []
        for title, content in structure.items():
            full_title = f"{prefix}{title}" if prefix else title
            sections.append(full_title)
            if isinstance(content, dict):
                sections.extend(self.flatten_structure(content, prefix=f"{full_title} > "))
        return sections

    # def update_content(self, title, new_content):
    #     try:
    #         self.contents[title] += new_content
    #         self.display_content(title)
    #     except TypeError as e:
    #         pass
    def update_content(self, path, new_content):
        if path in self.contents:
            self.contents[path] += new_content
            
    # def display_content(self, title):
    #     if self.contents[title].strip():
    #         self.placeholders[title].markdown(f"## {title}\n{self.contents[title]}")

    def display_structure(self, structure=None, level=1):
        if structure is None:
            structure = self.structure
            
        for title, content in structure.items():
            if self.contents[title].strip():  # Only display title if there is content
                st.markdown(f"{'#' * level} {title}")
                self.placeholders[title].markdown(self.contents[title])
            if isinstance(content, dict):
                self.display_structure(content, level + 1)

    def display_toc(self, structure, columns, level=1, col_index=0):
        for title, content in structure.items():
            with columns[col_index % len(columns)]:
                st.markdown(f"{' ' * (level-1) * 2}- {title}")
            col_index += 1
            if isinstance(content, dict):
                col_index = self.display_toc(content, columns, level + 1, col_index)
        return col_index

    def get_markdown_content(self, structure=None, level=1):
        """
        Returns the markdown styled pure string with the contents.
        """
        if structure is None:
            structure = self.structure
        
        markdown_content = f"# {self.book_title}\n\n" if level == 1 else ""
        
        for title, content in structure.items():
            current_path = f"{title}" if level == 1 else title
            if self.contents[current_path].strip():  # Only include title if there is content
                markdown_content += f"{'#' * level} {title}\n{self.contents[current_path]}\n\n"
            if isinstance(content, dict):
                markdown_content += self.get_markdown_content(content, level + 1)
        return markdown_content

    
    def initialize_contents(self, structure, path=""):
        contents = {}
        for title, content in structure.items():
            current_path = f"{path}/{title}" if path else title
            contents[current_path] = ""
            if isinstance(content, dict):
                contents.update(self.initialize_contents(content, current_path))
        return contents
    
    def create_sidebar(self):
        st.sidebar.title(self.book_title)
        
        def display_structure(structure, level=0, path=""):
            for title, content in structure.items():
                current_path = f"{path}/{title}" if path else title
                encoded_path = quote(current_path)
                
                if isinstance(content, dict):
                    st.sidebar.markdown(f"{'  ' * level}- **{title}**")
                    display_structure(content, level + 1, current_path)
                else:
                    if st.sidebar.button(f"{'  ' * level}- {title}", key=f"sidebar_{encoded_path}"):
                        st.experimental_set_query_params(section=encoded_path)
                        st.session_state.scroll_to_section = encoded_path
                        st.experimental_rerun()

        display_structure(self.structure)
    
    def display_content(self):
        def render_section(structure, level=2, path=""):
            for title, content in structure.items():
                current_path = f"{path}/{title}" if path else title
                section_id = f"section-{quote(current_path)}"
                
                st.markdown(f'<div id="{section_id}"></div>', unsafe_allow_html=True)
                st.markdown(f'<h{level}>{title}</h{level}>', unsafe_allow_html=True)
                
                if self.contents[current_path].strip():
                    with st.expander("Show/Hide Content", expanded=True):
                        st.markdown(self.contents[current_path])
                
                if isinstance(content, dict):
                    render_section(content, level + 1, current_path)
                
                st.markdown("---")  # Add a separator between sections

        render_section(self.structure)

        # Get the current section from URL parameters or session state
        query_params = st.experimental_get_query_params()
        current_section = query_params.get("section", [None])[0] or st.session_state.get("scroll_to_section")

        if current_section:
            st.markdown(f"""
                <script>
                    function attemptScroll() {{
                        var sectionId = "section-{current_section}";
                        var element = document.getElementById(sectionId);
                        if (element) {{
                            element.scrollIntoView({{behavior: "smooth", block: "start"}});
                            // Clear the scroll flag from session storage
                            sessionStorage.removeItem('scrollToSection');
                            return true;
                        }}
                        return false;
                    }}

                    function scrollWithRetry(maxAttempts = 10, interval = 200) {{
                        var attempts = 0;
                        var scrollInterval = setInterval(function() {{
                            if (attemptScroll() || attempts >= maxAttempts) {{
                                clearInterval(scrollInterval);
                            }}
                            attempts++;
                        }}, interval);
                    }}

                    // Set the scroll flag in session storage
                    sessionStorage.setItem('scrollToSection', '{current_section}');

                    // Attempt to scroll immediately
                    if (!attemptScroll()) {{
                        // If immediate scroll fails, start retry mechanism
                        scrollWithRetry();
                    }}
                </script>
                """, unsafe_allow_html=True)
            
            # Clear the scroll flag from session state
            if hasattr(st.session_state, 'scroll_to_section'):
                del st.session_state.scroll_to_section
    
    def display_download_buttons(self):
        col1, col2 = st.columns(2)
        
        with col1:
            markdown_file = self.create_markdown_file()
            st.download_button(
                label="Download Text",
                data=markdown_file,
                file_name=f'{self.book_title}.txt',
                mime='text/plain'
            )
        
        with col2:
            pdf_file = self.create_pdf_file()
            st.download_button(
                label="Download PDF",
                data=pdf_file,
                file_name=f'{self.book_title}.pdf',
                mime='application/pdf'
            )
                    
def create_markdown_file(content: str) -> BytesIO:
    """
    Create a Markdown file from the provided content.
    """
    markdown_file = BytesIO()
    markdown_file.write(content.encode("utf-8"))
    markdown_file.seek(0)
    return markdown_file


def create_pdf_file(content: str) -> BytesIO:
    """
    Create a PDF file from the provided Markdown content.
    Converts Markdown to styled HTML, then HTML to PDF.
    """

    html_content = markdown(content, extensions=["extra", "codehilite"])

    styled_html = f"""
    <html>
        <head>
            <style>
                @page {{
                    margin: 2cm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    font-size: 12pt;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #333366;
                    margin-top: 1em;
                    margin-bottom: 0.5em;
                }}
                p {{
                    margin-bottom: 0.5em;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 0.9em;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 1em;
                    border-radius: 4px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                blockquote {{
                    border-left: 4px solid #ccc;
                    padding-left: 1em;
                    margin-left: 0;
                    font-style: italic;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 1em;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                input, textarea {{
                    border-color: #4A90E2 !important;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
    </html>
    """

    pdf_buffer = BytesIO()
    HTML(string=styled_html).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    return pdf_buffer

def generate_book_title(prompt: str):
    """
    Generate a book title using AI.
    """
    completion = st.session_state.groq.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": "Generate suitable book titles for the provided topics. There is only one generated book title! Don't give any explanation or add any symbols, just write the title of the book. The requirement for this title is that it must be between 7 and 25 words long, and it must be attractive enough!"
            },
            {
                "role": "user",
                "content": f"Generate a book title for the following topic. There is only one generated book title! Don't give any explanation or add any symbols, just write the title of the book. The requirement for this title is that it must be at least 7 words and 25 words long, and it must be attractive enough:\n\n{prompt}"
            }
        ],
        temperature=0.7,
        max_tokens=100,
        top_p=1,
        stream=False,
        stop=None,
    )

    return completion.choices[0].message.content.strip()

def generate_book_structure(prompt: str):
    """
    Returns book structure content as well as total tokens and total time for generation.
    """
    completion = st.session_state.groq.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": 'Write in JSON format:\n\n{"Title of section goes here":"Description of section goes here",\n"Title of section goes here":{"Title of section goes here":"Description of section goes here","Title of section goes here":"Description of section goes here","Title of section goes here":"Description of section goes here"}}',
            },
            {
                "role": "user",
                "content": f"Write a comprehensive structure, omiting introduction and conclusion sections (forward, author's note, summary), for a long (>300 page) book. It is very important that use the following subject and additional instructions to write the book. \n\n<subject>{prompt}</subject>\n\n<additional_instructions>{additional_instructions}</additional_instructions>",
            },
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )

    usage = completion.usage
    statistics_to_return = GenerationStatistics(
        input_time=usage.prompt_time,
        output_time=usage.completion_time,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        total_time=usage.total_time,
        model_name="llama3-70b-8192",
    )

    return statistics_to_return, completion.choices[0].message.content


def generate_section(prompt: str, additional_instructions: str):
    stream = st.session_state.groq.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": "You are an expert writer. Generate a long, comprehensive, structured chapter for the section provided. If additional instructions are provided, consider them very important. Only output the content.",
            },
            {
                "role": "user",
                "content": f"Generate a long, comprehensive, structured chapter. Use the following section and important instructions:\n\n<section_title>{prompt}</section_title>\n\n<additional_instructions>{additional_instructions}</additional_instructions>",
            },
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in stream:
        tokens = chunk.choices[0].delta.content
        if tokens:
            yield tokens
        if x_groq := chunk.x_groq:
            if not x_groq.usage:
                continue
            usage = x_groq.usage
            statistics_to_return = GenerationStatistics(
                input_time=usage.prompt_time,
                output_time=usage.completion_time,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                total_time=usage.total_time,
                model_name="llama3-8b-8192",
            )
            yield statistics_to_return

def navigate_to_section(title):
    st.session_state.current_section = title
    
# Initialize
if "button_disabled" not in st.session_state:
    st.session_state.button_disabled = False

if "button_text" not in st.session_state:
    st.session_state.button_text = "Generate"

if "statistics_text" not in st.session_state:
    st.session_state.statistics_text = ""

if 'book_title' not in st.session_state:
    st.session_state.book_title = ""

# Initialize session state variables
if 'current_section' not in st.session_state:
    st.session_state.current_section = "Book Generation"

st.write(
    """
# Groqbook: Write full books using llama3 (8b and 70b) on Groq
"""
)


def disable():
    st.session_state.button_disabled = True


def enable():
    st.session_state.button_disabled = False


def empty_st():
    st.empty()


# Add this function to create the toggle section
def create_toggle_section():
    st.sidebar.title("Navigation")
    sections = ["Book Generation", "Statistics", "About"]
    st.session_state.current_section = st.sidebar.radio("Go to", sections)

# Add this function for the About section
def show_about_section():
    st.write("""
    # About Groqbook
    
    Groqbook is an AI-powered tool that generates full books using the llama3 (8b and 70b) models on Groq.
    
    ## Features:
    - Generate book titles and structures
    - Create comprehensive content for each section
    - Download generated books in markdown or PDF format
    - View generation statistics
    
    ## How to use:
    1. Enter your Groq API Key
    2. Provide a book topic and any additional instructions
    3. Click 'Generate' to start the book creation process
    4. View statistics and download your book when it's ready
    
    For more information, visit [Groq's website](https://groq.com/).
    """)

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Book Generation", "Statistics", "About"])

with tab1:
    try:
        with st.form("groqform"):
            if not GROQ_API_KEY:
                groq_input_key = st.text_input(
                    "Enter your Groq API Key (gsk_yA...):", "", type="password"
                )   

            topic_text = st.text_input(
                "What do you want the book to be about?",
                value="",
                help="Enter the main topic or title of your book",
            )   

            additional_instructions = st.text_area(
                "Additional Instructions (optional)",
                help="Provide any specific guidelines or preferences for the book's content",
                placeholder="E.g., 'Focus on beginner-friendly content', 'Include case studies', etc.",
                value="",
            )   

            # Generate button
            submitted = st.form_submit_button(
                st.session_state.button_text,
                on_click=disable,
                disabled=st.session_state.button_disabled,
            )   

            # Statistics
            placeholder = st.empty()    

            def display_statistics():
                with placeholder.container():
                    if st.session_state.statistics_text:
                        if (
                            "Generating structure in background"
                            not in st.session_state.statistics_text
                        ):
                            st.markdown(
                                st.session_state.statistics_text + "\n\n---\n"
                            )  # Format with line if showing statistics
                        else:
                            st.markdown(st.session_state.statistics_text)
                    else:
                        placeholder.empty() 

            if submitted:
                if len(topic_text) < 10:
                    raise ValueError("Book topic must be at least 10 characters long")  

                st.session_state.button_disabled = True
                st.session_state.statistics_text = "Generating book title and structure in background...."
                display_statistics()    

                if not GROQ_API_KEY:
                    st.session_state.groq = Groq(api_key=groq_input_key)    

                large_model_generation_statistics, book_structure = generate_book_structure(
                    topic_text
                )
                # Generate AI book title
                st.session_state.book_title = generate_book_title(topic_text)
                st.write(f"## {st.session_state.book_title}")   

                large_model_generation_statistics, book_structure = generate_book_structure(topic_text) 

                total_generation_statistics = GenerationStatistics(
                    model_name="llama3-8b-8192"
                )   
                
                try:
                    book_structure_json = json.loads(book_structure)
                    book = Book(st.session_state.book_title, book_structure_json)

                    if 'book' not in st.session_state:
                        st.session_state.book = book    
                    
                    # Print the book structure to the terminal to show structure
                    print(json.dumps(book_structure_json, indent=2))    

                    st.session_state.book.create_sidebar()
                    st.session_state.book.display_content()
                    
                    # def stream_section_content(sections):
                    #     for title, content in sections.items():
                    #         if isinstance(content, str):
                    #             content_stream = generate_section(
                    #                 title + ": " + content, additional_instructions
                    #             )
                    #             for chunk in content_stream:
                    #                 # Check if GenerationStatistics data is returned instead of str tokens
                    #                 chunk_data = chunk
                    #                 if type(chunk_data) == GenerationStatistics:
                    #                     total_generation_statistics.add(chunk_data) 

                    #                     st.session_state.statistics_text = str(
                    #                         total_generation_statistics
                    #                     )
                    #                     display_statistics()    

                    #                 elif chunk != None:
                    #                     st.session_state.book.update_content(title, chunk)
                    #         elif isinstance(content, dict):
                    #             stream_section_content(content) 
                    def stream_section_content(sections, path=""):
                        for title, content in sections.items():
                            current_path = f"{path}/{title}" if path else title
                            if isinstance(content, str):
                                content_stream = generate_section(
                                    title + ": " + content, additional_instructions
                                )
                                for chunk in content_stream:
                                    if isinstance(chunk, GenerationStatistics):
                                        total_generation_statistics.add(chunk)
                                        st.session_state.statistics_text = str(total_generation_statistics)
                                        display_statistics()
                                    elif chunk is not None:
                                        st.session_state.book.update_content(current_path, chunk)
                            elif isinstance(content, dict):
                                stream_section_content(content, current_path)

                    st.write("Debug: Starting content generation")
                    stream_section_content(book_structure_json)
                    st.write("Debug: Content generation completed")
            
                    st.session_state.book.create_sidebar()
                    st.session_state.book.display_content()
                    
                except json.JSONDecodeError:
                    st.error("Failed to decode the book structure. Please try again.")  

                enable()
                    
        if st.button("End Generation and Download Book"):
            if "book" in st.session_state:
                # Create markdown file
                st.write(str(st.session_state.book.get_markdown_content()))
                
                markdown_file = create_markdown_file(
                    st.session_state.book.get_markdown_content()
                )
                st.download_button(
                    label="Download Text",
                    data=markdown_file,
                    file_name=f'{st.session_state.book_title}.txt',
                    mime='text/plain'
                )   

                # # Create pdf file (styled)
                # pdf_file = create_pdf_file(st.session_state.book.get_markdown_content())
                # st.download_button(
                #     label="Download PDF",
                #     data=pdf_file,
                #     file_name=f'{st.session_state.book_title}.pdf',
                #     mime='application/pdf'
                # )
            else:
                raise ValueError("Please generate content first before downloadin the  book.")  

    except Exception as e:
        st.session_state.button_disabled = False
        st.error(e) 

        if st.button("Clear"):
            st.rerun()

with tab2:
    st.write("# Generation Statistics")
    if "statistics_text" in st.session_state and st.session_state.statistics_text:
        st.markdown(st.session_state.statistics_text)
    else:
        st.write("No statistics available. Generate a book to see statistics.")

with tab3:
    show_about_section()

# At the end of the script, add:
if 'book' in st.session_state:
    st.session_state.book.create_sidebar()
    st.session_state.book.display_content()
    
    
st.markdown("""
    <script>
        // Check if we need to scroll on page load
        window.addEventListener('load', function() {
            var scrollToSection = sessionStorage.getItem('scrollToSection');
            if (scrollToSection) {
                var element = document.getElementById("section-" + scrollToSection);
                if (element) {
                    element.scrollIntoView({behavior: "smooth", block: "start"});
                    sessionStorage.removeItem('scrollToSection');
                }
            }
        });
    </script>
    """, unsafe_allow_html=True)