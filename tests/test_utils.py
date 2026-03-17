"""Tests for genesis.utils module."""

import numpy as np
import pytest

from genesis.utils.config import Config, load_config
from genesis.utils.geometry import SE3, SO3
from genesis.utils.types import BoundingBox, Transform


class TestConfig:
    """测试 Config 类。"""
    
    def test_create_empty_config(self):
        """测试创建空配置。"""
        cfg = Config()
        assert cfg._cfg is not None
    
    def test_config_from_dict(self):
        """测试从字典创建配置。"""
        d = {"world": {"size": [50.0, 50.0]}}
        cfg = Config.from_dict(d)
        assert cfg.world.size == [50.0, 50.0]
    
    def test_config_getattr(self):
        """测试点号访问。"""
        cfg = Config.from_dict({"a": {"b": {"c": 1}}})
        assert cfg.a.b.c == 1
    
    def test_config_setattr(self):
        """测试点号设置。"""
        cfg = Config()
        cfg.world = {"size": [10, 10]}
        assert cfg.world.size == [10, 10]
    
    def test_config_merge(self):
        """测试配置合并。"""
        cfg1 = Config.from_dict({"a": 1, "b": 2})
        cfg2 = Config.from_dict({"b": 3, "c": 4})
        merged = cfg1.merge(cfg2)
        assert merged.a == 1
        assert merged.b == 3
        assert merged.c == 4
    
    def test_config_to_dict(self):
        """测试转换为字典。"""
        cfg = Config.from_dict({"a": 1, "b": {"c": 2}})
        d = cfg.to_dict()
        assert d["a"] == 1
        assert d["b"]["c"] == 2


class TestSO3:
    """测试 SO3 旋转类。"""
    
    def test_identity_rotation(self):
        """测试单位旋转。"""
        R = SO3.identity()
        assert R.quaternion == (1.0, 0.0, 0.0, 0.0)
    
    def test_rotation_matrix_orthogonal(self):
        """测试旋转矩阵正交性。"""
        R = SO3.random()
        mat = R.to_rotation_matrix()
        # 检查正交性: R^T * R = I
        assert np.allclose(mat @ mat.T, np.eye(3))
        # 检查行列式为 1
        assert np.isclose(np.linalg.det(mat), 1.0)
    
    def test_rotation_inverse(self):
        """测试旋转逆。"""
        R = SO3.random()
        R_inv = R.inverse()
        # R * R^-1 = I
        mat = R.to_rotation_matrix() @ R_inv.to_rotation_matrix()
        assert np.allclose(mat, np.eye(3))
    
    def test_rotation_composition(self):
        """测试旋转组合。"""
        R1 = SO3.random()
        R2 = SO3.random()
        R12 = R1 * R2
        # 检查矩阵乘法
        mat = R1.to_rotation_matrix() @ R2.to_rotation_matrix()
        assert np.allclose(R12.to_rotation_matrix(), mat)
    
    def test_from_euler_angles(self):
        """测试从欧拉角创建。"""
        roll, pitch, yaw = 0.1, 0.2, 0.3
        R = SO3.from_euler_angles(roll, pitch, yaw)
        euler = R.to_euler_angles()
        assert np.allclose(euler, (roll, pitch, yaw), atol=1e-6)
    
    def test_from_axis_angle(self):
        """测试从轴角创建。"""
        axis = np.array([0, 0, 1.0])
        angle = np.pi / 4
        R = SO3.from_axis_angle(axis, angle)
        # 绕 z 轴旋转 45 度
        mat = R.to_rotation_matrix()
        expected = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        assert np.allclose(mat, expected)


class TestSE3:
    """测试 SE3 变换类。"""
    
    def test_identity_transform(self):
        """测试单位变换。"""
        T = SE3.identity()
        assert T.position == (0.0, 0.0, 0.0)
        assert T.rotation.quaternion == (1.0, 0.0, 0.0, 0.0)
    
    def test_transform_inverse(self):
        """测试变换逆。"""
        T = SE3.from_pose(1, 2, 3, 0.1, 0.2, 0.3)
        T_inv = T.inverse()
        # T * T^-1 = I
        mat = T.to_matrix() @ T_inv.to_matrix()
        assert np.allclose(mat, np.eye(4))
    
    def test_transform_point(self):
        """测试点变换。"""
        T = SE3.from_translation(1, 2, 3)
        p = T.transform_point((0, 0, 0))
        assert p == (1.0, 2.0, 3.0)
    
    def test_transform_composition(self):
        """测试变换组合。"""
        T1 = SE3.from_translation(1, 0, 0)
        T2 = SE3.from_translation(0, 2, 0)
        T12 = T1 * T2
        assert T12.position == (1.0, 2.0, 0.0)
    
    def test_from_matrix(self):
        """测试从矩阵创建。"""
        mat = np.eye(4)
        mat[0, 3] = 1.0
        mat[1, 3] = 2.0
        mat[2, 3] = 3.0
        T = SE3.from_matrix(mat)
        assert T.position == (1.0, 2.0, 3.0)


class TestBoundingBox:
    """测试边界框类。"""
    
    def test_bounding_box_size(self):
        """测试边界框尺寸。"""
        bbox = BoundingBox(min=(0, 0, 0), max=(1, 2, 3))
        assert bbox.size == (1.0, 2.0, 3.0)
    
    def test_bounding_box_center(self):
        """测试边界框中心。"""
        bbox = BoundingBox(min=(0, 0, 0), max=(2, 2, 2))
        assert bbox.center == (1.0, 1.0, 1.0)
    
    def test_bounding_box_volume(self):
        """测试边界框体积。"""
        bbox = BoundingBox(min=(0, 0, 0), max=(2, 3, 4))
        assert bbox.volume == 24.0
    
    def test_bounding_box_contains(self):
        """测试点包含。"""
        bbox = BoundingBox(min=(0, 0, 0), max=(1, 1, 1))
        assert bbox.contains((0.5, 0.5, 0.5))
        assert not bbox.contains((1.5, 0.5, 0.5))
    
    def test_bounding_box_intersects(self):
        """测试边界框相交。"""
        bbox1 = BoundingBox(min=(0, 0, 0), max=(1, 1, 1))
        bbox2 = BoundingBox(min=(0.5, 0.5, 0.5), max=(1.5, 1.5, 1.5))
        assert bbox1.intersects(bbox2)
        
        bbox3 = BoundingBox(min=(2, 2, 2), max=(3, 3, 3))
        assert not bbox1.intersects(bbox3)


class TestTransform:
    """测试 Transform 类。"""
    
    def test_transform_to_matrix(self):
        """测试变换转矩阵。"""
        t = Transform(position=(1, 2, 3), rotation=(1, 0, 0, 0))
        mat = t.to_matrix()
        expected = np.array([
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 3],
            [0, 0, 0, 1],
        ])
        assert np.allclose(mat, expected)
    
    def test_transform_inverse(self):
        """测试变换逆。"""
        t = Transform(position=(1, 2, 3), rotation=(1, 0, 0, 0))
        t_inv = t.inverse()
        mat = t.to_matrix() @ t_inv.to_matrix()
        assert np.allclose(mat, np.eye(4))
