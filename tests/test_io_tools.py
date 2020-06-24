from jnrr import io_tools


def test_extract_emd():
    io_tools.extract_emd("data/sample_data.emd",
                         output_folder=None, prefix="frame",
                         image_dataset_index=None,
                         spectrum_dataset_index=None,
                         digits=None, image_post_processing=None,
                         frames=None)
