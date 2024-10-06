import streamlit as st
import numpy as np
import cv2
import rasterio
from tensorflow.keras.models import load_model
import leafmap.foliumap as leafmap
import os
import gdown



os.makedirs("./uploaded_files/original/", exist_ok=True)
os.makedirs("./uploaded_files/output_tif/", exist_ok=True)


# Function to download the file from Google Drive
def download_from_drive(file_id, output):
    gdown.download(f"https://drive.google.com/uc?id={file_id}", output, quiet=False)

# Load your pre-trained model
model = load_model('./unet_model_3k.keras')

# Function for extracting the predicted image
def predict_from_tif(model, tif_file_path):
    with rasterio.open(tif_file_path) as src:
        image_array = src.read()
        image_array = np.transpose(image_array, (1, 2, 0))  # HWC format
    image_resized = cv2.resize(image_array, (256, 256))  # Resizing to (256, 256)
    img_array = np.expand_dims(image_resized, axis=0) / 255.0  # Normalizing and expanding dims
    predictions = model.predict(img_array)
    return predictions

# Function to create a new TIFF file for the predicted image
def create_tiff_with_metadata(original_tiff_path, new_image_data, new_tiff_path):
    new_image_data = (new_image_data * 255).astype(np.uint8)  # Convert to uint8 for saving
    new_image_data = np.transpose(new_image_data, (2, 0, 1))  # Converting to CHW format
    with rasterio.open(original_tiff_path) as src:
        crs = src.crs
        transform = src.transform
        width = src.width
        height = src.height
        dtype = src.dtypes[0]
    with rasterio.open(new_tiff_path, 'w', driver='GTiff', height=height, width=width, count=1, dtype=dtype, crs=crs, transform=transform) as dst:
        dst.write(new_image_data)

# Google Drive file IDs
before_image_id = "1NSS_Xsv48fSucMtNHfqolP1R3HK7gK7O"  # Before image file ID
after_image_id = "10PeRkH6LU5AUxnCtSUUnrJ8mOa_30elb"   # After image file ID

# Default paths for images if not uploaded
before_image_path = './monsia.tif'
after_image_path = './roadsmonsiamerquator_1.tif'

# File uploader for images
uploaded_file = st.sidebar.file_uploader('Upload an image', type=['tiff', 'tif'])

if uploaded_file is not None:  
    file_type = uploaded_file.type

    # If the uploaded file is a TIFF image
    if file_type in ['image/tiff', 'image/tif']:
        save_path = f"./uploaded_files/original/{uploaded_file.name}"
        output_path = f"./uploaded_files/output_tif/{uploaded_file.name}"

        # Save the uploaded file to the specified path
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"File saved successfully at {save_path}!")

        # Predict and create the new TIFF file
        predictions = predict_from_tif(model, save_path)
        create_tiff_with_metadata(save_path, predictions[0], output_path)

        before_image_path = save_path
        after_image_path = output_path

    else:
        st.write("Please upload a .tif file")
else:
    # Download files from Google Drive if no file is uploaded
    download_from_drive(before_image_id, before_image_path)
    download_from_drive(after_image_id, after_image_path)

# Load the list of uploaded original and output files
original_files = os.listdir("./uploaded_files/original/")
output_files = os.listdir("./uploaded_files/output_tif/")

# Create full paths
before_image_paths = [f"./uploaded_files/original/{file}" for file in original_files if file.endswith(('.tiff', '.tif'))]
after_image_paths = [f"./uploaded_files/output_tif/{file}" for file in output_files if file.endswith(('.tiff', '.tif'))]

# Display the split-panel map in Streamlit
st.title("Split-panel Map")
with st.expander("See source code"):
    with st.echo():
        # Create the map and add split-panel functionality
        m = leafmap.Map(minimap_control=True)
        m.add_basemap('CartoDB.DarkMatter')

        # Add the uploaded images to the map as layers
        if before_image_paths and after_image_paths:
            for before_path in before_image_paths:
                m.add_raster(before_path, layer_name=os.path.basename(before_path), layer_id='original')
            for after_path in after_image_paths:
                m.add_raster(after_path, layer_name=os.path.basename(after_path), layer_id='processed')

        # Display the split map using the first processed file and original file
        m.split_map(left_layer=before_image_path, right_layer=after_image_path)

# Display the map
m.to_streamlit(height=700)
