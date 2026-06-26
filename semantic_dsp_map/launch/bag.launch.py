"""Launch the semantic_dsp_map pipeline against the recorded bag.

Bag location: ~/semantic_map_ws/bag/
Key bag topics used:
  /lidar/merged/points              → depth image (via lidar_to_depth)
  /bnk/omninav_combine/out_lo       → pose      (via odom_to_pose)
  /cam/left/camera_info             → camera intrinsics for projection

Play the bag in a separate terminal BEFORE or AFTER starting this launch:
  ros2 bag play ~/semantic_map_ws/bag --clock --loop

The '--clock' flag makes the bag publish /clock so all nodes use sim time.

If the TF between the lidar frame and the camera frame is not present in the bag
(check with: ros2 bag info ~/semantic_map_ws/bag), you may need to publish a
static transform.  Example (lidar_frame → cam_left):
  ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 lidar_frame cam_left
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('semantic_dsp_map')
    cfg = PathJoinSubstitution([pkg, 'cfg', 'options_bag.yaml'])

    # ── tuneable arguments ─────────────────────────────────────────────────────
    lidar_topic_arg = DeclareLaunchArgument(
        'lidar_topic', default_value='/lidar/merged/points',
        description='LiDAR merged point cloud topic from the bag')
    odom_topic_arg  = DeclareLaunchArgument(
        'odom_topic',  default_value='/bnk/omninav_combine/out_lo',
        description='Odometry topic from the bag')
    cam_frame_arg   = DeclareLaunchArgument(
        'camera_frame', default_value='',
        description='Camera TF frame (leave empty to auto-detect from CameraInfo)')
    max_depth_arg   = DeclareLaunchArgument(
        'max_depth', default_value='30.0',
        description='Maximum depth (m) to project from LiDAR')

    # ── nodes ──────────────────────────────────────────────────────────────────
    odom_to_pose = Node(
        package='semantic_dsp_map',
        executable='odom_to_pose.py',
        name='odom_to_pose',
        parameters=[{
            'input_topic':  LaunchConfiguration('odom_topic'),
            'output_topic': '/camera/pose_from_odom',
            'use_sim_time': True,
        }],
        output='screen',
    )

    lidar_to_depth = Node(
        package='semantic_dsp_map',
        executable='lidar_to_depth.py',
        name='lidar_to_depth',
        parameters=[{
            'lidar_topic':       LaunchConfiguration('lidar_topic'),
            'camera_info_topic': '/cam/left/camera_info',
            'output_topic':      '/camera/depth_from_lidar',
            'camera_frame':      LaunchConfiguration('camera_frame'),
            'max_depth':         LaunchConfiguration('max_depth'),
            'use_sim_time':      True,
        }],
        output='screen',
    )

    dummy_masks = Node(
        package='semantic_dsp_map',
        executable='dummy_mask_publisher.py',
        name='dummy_mask_publisher',
        parameters=[{
            'depth_topic':  '/camera/depth_from_lidar',
            'output_topic': '/mask_group_bag',
            'use_sim_time': True,
        }],
        output='screen',
    )

    mapping = Node(
        package='semantic_dsp_map',
        executable='mapping',
        name='semantic_mapping',
        arguments=[cfg],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'zed2.rviz'])],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        lidar_topic_arg,
        odom_topic_arg,
        cam_frame_arg,
        max_depth_arg,
        odom_to_pose,
        lidar_to_depth,
        dummy_masks,
        mapping,
        rviz,
    ])
