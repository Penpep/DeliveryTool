
import streamlit as st
from PIL import Image, ImageDraw
import io

st.set_page_config(page_title="Layout Labeling Tool", layout="wide")
st.title("📝 Interactive Layout Labeling Tool (Streamlit)")

# Upload layout image
uploaded_file = st.file_uploader("Upload your layout image", type=["png", "jpg", "jpeg"])
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Initialize session state
    if "labels" not in st.session_state:
        st.session_state.labels = []
    if "delete_mode" not in st.session_state:
        st.session_state.delete_mode = False

    # Display mode toggle
    if st.button(f"Switch to {'Delete' if not st.session_state.delete_mode else 'Label'} Mode"):
        st.session_state.delete_mode = not st.session_state.delete_mode

    st.write(f"**Current Mode:** {'🗑️ Delete' if st.session_state.delete_mode else '🔤 Label'}")

    # Display image and get click
    click = st.image(image, use_column_width=False)

    # Get coordinates manually (simplified for Streamlit)
    x = st.number_input("X Coordinate (pixels)", min_value=0, max_value=width, value=10)
    y = st.number_input("Y Coordinate (pixels)", min_value=0, max_value=height, value=10)
    if st.button("Click Here"):
        if st.session_state.delete_mode:
            # Try deleting a label near the clicked point
            to_remove = None
            for i, (lx, ly, text) in enumerate(st.session_state.labels):
                if abs(x - lx) < 30 and abs(y - ly) < 15:
                    to_remove = i
                    break
            if to_remove is not None:
                st.session_state.labels.pop(to_remove)
        else:
            label = st.text_input("Enter Label Text", key=f"label_{x}_{y}")
            if label:
                st.session_state.labels.append((x, y, label))

    # Redraw all labels
    labeled_img = image.copy()
    draw = ImageDraw.Draw(labeled_img)
    for lx, ly, text in st.session_state.labels:
        draw.text((lx, ly), text, fill="white")

    st.image(labeled_img, caption="Labeled Layout", use_column_width=False)

    # Save final labeled image
    buf = io.BytesIO()
    labeled_img.save(buf, format="PNG")
    st.download_button("Download Labeled Image", data=buf.getvalue(), file_name="labeled_layout.png", mime="image/png")
