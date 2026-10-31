# Verified model assets

The ONNX files were manually supplied from the official `opencv/opencv_zoo`
repository. This implementation does not download, convert, rename, or replace
them at startup. Their sizes and SHA-256 values are verified before loading.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| face_detection_yunet_2026may.onnx | 229738 | ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0 |
| face_recognition_sface_2021dec.onnx | 38696353 | 0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79 |

YuNet source and OpenCV 5.x dynamic-input notes:
https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet

SFace source:
https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface

Upstream redistribution licenses are preserved in `LICENSE-YuNet.txt` (MIT,
Copyright 2020 Shiqi Yu) and `LICENSE-SFace.txt` (Apache License 2.0).
These texts were retrieved from the model directories' respective `LICENSE`
files, not inferred from the repository's general license. Include these
notices when distributing the models.

Upstream license URLs:
https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/LICENSE
https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE

Validated environment: Windows x64, Python 3.11.8, opencv-python distribution
5.0.0.93 (`cv2.__version__ == 5.0.0`), NumPy 2.4.6. Dependency declarations
match the already installed versions; no package installation was performed.
