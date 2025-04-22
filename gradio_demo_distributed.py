from loguru import logger
import gradio as gr
from gradio_main_distributed import main, init

# Paths can be a list of strings or pathlib.Path objects
# corresponding to filenames or directories.
# https://www.gradio.app/docs/gradio/set_static_paths
# !Important, if you do not define like that, a file will be located in a temp and uncontrolled path
gr.set_static_paths(paths=["video-fetch-and-trim/videos/"])


N_VIDEOS = 4
video_list = init(n_videos=N_VIDEOS)


logger.info(f"Trending videos: {video_list}")
# print(f"Trending videos: {video_list}")

# This JS will be injected once and run when the app loads
custom_js = """
() => {
    const playAll = () => {
        const videos = document.querySelectorAll("video");
        videos.forEach(v => {
            v.play().catch(err => console.warn("Video play failed:", err));
        });
    };

    // Add global listener for button with specific ID
    setTimeout(() => {
        const btn = document.getElementById("play-all-button");
        if (btn) {
            btn.addEventListener("click", playAll);
        }
    }, 500);
}
"""

# Global index to track the current video
current_index = 0


def select_video(selected_video: str):
    """Update the current index based on the selected video and return that video."""
    global current_index
    try:
        current_index = video_list.index(selected_video)
    except ValueError:
        current_index = 0
    return video_list[current_index]


def get_next_video():
    """Cycle to the next video and return it."""
    global current_index
    current_index = (current_index + 1) % len(video_list)
    return video_list[current_index]


def update_display_video(video_url: str):
    return gr.update(elem_id="video-display", value=video_url)


def retrieve_related_videos(video_url: str):
    global video_list

    retrieved_videos = main(video_url=video_url)
    video_list = retrieved_videos.videos

    video_list = list(dict.fromkeys(video_list))  # remove duplicate

    return [
        gr.update(elem_id=f"recommended-video-{i}")
        if i >= len(video_list)
        else gr.update(elem_id=f"recommended-video-{i}", value=video_list[i])
        for i in range(N_VIDEOS)
    ]


# def stream_video(video_path):
#     # Stream logic here
#     yield video_path


with gr.Blocks(js=custom_js) as demo:
    gr.Markdown("## TikTok2 Simulator Recommended Videos")

    with gr.Row():
        video_display = gr.Video(
            value=video_list[0],
            label="Video Player",
            autoplay=True,
            loop=True,
            interactive=False,
            elem_id="video-display",
            # streaming=True,  # TODO
        )

    # Button to load the next video from the list.
    next_button = gr.Button("▶ Next")

    gr.Button("▶ Play all recommended videos", elem_id="play-all-button")

    recommended_videos_display = []
    with gr.Row():
        for i, video_path in enumerate(video_list[:N_VIDEOS]):
            with gr.Column():
                recommended_videos_display += [
                    gr.Video(
                        elem_id=f"recommended-video-{i}",
                        value=video_path,
                        label=None,
                        autoplay=True,
                        loop=True,
                        interactive=False,
                        show_label=False,
                        # streaming=True,  # TODO
                    )
                ]
                gr.Button(f"▶ Video {i + 1}", elem_id=f"select-btn-{i}").click(
                    fn=update_display_video,
                    inputs=[recommended_videos_display[-1]],
                    outputs=video_display,
                )

    # When the next button is clicked, display the next video.
    next_button.click(fn=get_next_video, outputs=video_display)
    video_display.change(
        fn=retrieve_related_videos,
        inputs=[video_display],
        outputs=recommended_videos_display,
    )

demo.launch()
