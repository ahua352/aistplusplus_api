# coding=utf-8
# Copyright 2020 The Google AI Perception Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Demo code for running visualizer."""
import os

from absl import app
from absl import flags
from aist_plusplus.loader import AISTDataset
from aist_plusplus.visualizer import plot_on_video
from smplx import SMPL
import torch

FLAGS = flags.FLAGS
flags.DEFINE_string(
    'anno_dir',
    '/home/ruilongli/data/AIST++/',
    'input local dictionary for AIST++ annotations.')
flags.DEFINE_string(
    'video_dir',
    '/home/ruilongli/data/AIST/videos/10M/',
    'input local dictionary for AIST Dance Videos.')
flags.DEFINE_string(
    'smpl_dir',
    '/home/ruilongli/data/smpl_model/smpl',
    'input local dictionary that stores SMPL data.')
flags.DEFINE_string(
    'video_name',
    'gBR_sBM_c01_d04_mBR0_ch01',
    'input video name to be visualized.')
flags.DEFINE_string(
    'save_dir',
    './',
    'output local dictionary that stores AIST++ visualization.')
flags.DEFINE_enum(
    'mode', '2D', ['2D', '3D', 'SMPL', 'SMPLMesh'],
    'visualize 3D or 2D keypoints, or SMPL joints on image plane.')


def main(_):
  # Parsing data info.
  aist_dataset = AISTDataset(FLAGS.anno_dir)
  video_path = os.path.join(FLAGS.video_dir, f'{FLAGS.video_name}.mp4')
  seq_name, view = AISTDataset.get_seq_name(FLAGS.video_name)
  view_idx = AISTDataset.VIEWS.index(view)

  # Parsing keypoints.
  if FLAGS.mode == '2D':  # raw keypoints detection results.
    keypoints2d, _, _ = AISTDataset.load_keypoint2d(
        aist_dataset.keypoint2d_dir, seq_name)
    keypoints2d = keypoints2d[view_idx, :, :, 0:2]

  elif FLAGS.mode == '3D':  # 3D keypoints with temporal optimization.
    keypoints3d = AISTDataset.load_keypoint3d(
        aist_dataset.keypoint3d_dir, seq_name, use_optim=True)
    nframes, njoints, _ = keypoints3d.shape
    env_name = aist_dataset.mapping_seq2env[seq_name]
    cgroup = AISTDataset.load_camera_group(aist_dataset.camera_dir, env_name)
    keypoints2d = cgroup.project(keypoints3d)
    keypoints2d = keypoints2d.reshape(9, nframes, njoints, 2)[view_idx]

  elif FLAGS.mode == 'SMPL':  # SMPL joints
    smpl_poses, smpl_scaling, smpl_trans = AISTDataset.load_motion(
        aist_dataset.motion_dir, seq_name)
    smpl = SMPL(model_path=FLAGS.smpl_dir, gender='MALE', batch_size=1)
    keypoints3d = smpl.forward(
        global_orient=torch.from_numpy(smpl_poses[:, 0:1]).float(),
        body_pose=torch.from_numpy(smpl_poses[:, 1:]).float(),
        transl=torch.from_numpy(smpl_trans).float(),
        scaling=torch.from_numpy(smpl_scaling.reshape(1, 1)).float(),
        ).joints.detach().numpy()

    nframes, njoints, _ = keypoints3d.shape
    env_name = aist_dataset.mapping_seq2env[seq_name]
    cgroup = AISTDataset.load_camera_group(aist_dataset.camera_dir, env_name)
    keypoints2d = cgroup.project(keypoints3d)
    keypoints2d = keypoints2d.reshape(9, nframes, njoints, 2)[view_idx]

  elif FLAGS.mode == 'SMPLMesh':  # SMPL Mesh
    import vedo  # install by `pip install vedo`
    import time
    smpl_poses, smpl_scaling, smpl_trans = AISTDataset.load_motion(
        aist_dataset.motion_dir, seq_name)
    smpl = SMPL(model_path=FLAGS.smpl_dir, gender='MALE', batch_size=1)
    vertices = smpl.forward(
        global_orient=torch.from_numpy(smpl_poses[:, 0:1]).float(),
        body_pose=torch.from_numpy(smpl_poses[:, 1:]).float(),
        transl=torch.from_numpy(smpl_trans).float(),
        scaling=torch.from_numpy(smpl_scaling.reshape(1, 1)).float(),
        ).vertices.detach().numpy()
    faces = smpl.faces

    plotter = vedo.Plotter(interactive=False)

    for verts in vertices:
        plotter.clear() 

        mesh = vedo.Mesh([verts, faces])
        mesh.color([200, 200, 250])    
        
        plotter.add(mesh)
        plotter.show(interactive=False)

        time.sleep(0.01)
    exit()

  # Visualize.
  os.makedirs(FLAGS.save_dir, exist_ok=True)
  save_path = os.path.join(FLAGS.save_dir, f'{FLAGS.video_name}.mp4')
  plot_on_video(keypoints2d, video_path, save_path, fps=60)


if __name__ == '__main__':
  app.run(main)

