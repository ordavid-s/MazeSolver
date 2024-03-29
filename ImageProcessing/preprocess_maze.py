#!/usr/bin/env python
# coding: utf-8

# In[25]:

"""
Maze preprocess methods and classes
"""

import cv2
import math
import numpy as np
from skimage.morphology import skeletonize

from config import Config

# value to use for the maze lines
MAZE_COLOR = 255
# value to use for the background
BACKGROUND_COLOR = 0


def load_raw_image(path):
    """
    loads image from path
    :param path:
    :return: numpy array
    """
    # Load using opencv
    raw_image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    # convert your lists into a numpy array of size (N, C, H, W)
    return np.array(raw_image)


def cyclic_intersection_pts(pts):
    """
    Sorts 4 points in clockwise direction with the first point been closest to 0,0
    Assumption:
        There are exactly 4 points in the input and
        from a rectangle which is not very distorted
    """
    if pts.shape[0] != 4:
        return None

    # Calculate the center
    center = np.mean(pts, axis=0)

    # Sort the points in clockwise
    cyclic_pts = [
        # Top-left
        pts[np.where(np.logical_and(pts[:, 0] < center[0], pts[:, 1] < center[1]))[0][0], :],
        # Top-right
        pts[np.where(np.logical_and(pts[:, 0] > center[0], pts[:, 1] < center[1]))[0][0], :],
        # Bottom-Right
        pts[np.where(np.logical_and(pts[:, 0] > center[0], pts[:, 1] > center[1]))[0][0], :],
        # Bottom-Left
        pts[np.where(np.logical_and(pts[:, 0] < center[0], pts[:, 1] > center[1]))[0][0], :]
    ]

    return np.array(cyclic_pts)


def get_best_fit_quad(contour):
    hull = cv2.convexHull(contour, False)
    best_points = []
    best_area = 0
    for i in range(len(hull)):
        x1, y1 = hull[i][0]
        for j in range(i+1, len(hull)):
            x2, y2 = hull[j][0]
            for k in range(j+1, len(hull)):
                x3, y3 = hull[k][0]
                for l in range(k+1, len(hull)):
                    x4, y4 = hull[l][0]
                    a = (x1*y2 - x2*y1) + (x2*y3 - x3*y2) + (x3*y4 - x4*y3) + (x4*y1 - x1*y4)
                    if a > best_area:
                        best_points = [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
                        best_area = a
    return np.array(best_points)

def warp_image(img, mask, buffer=30):
    """
    warps the image so the corners are the maze corners
    :param img: img to warp
    :param thresh: thresholded image
    :param buffer: amount of padding to give around the recognized rectangle
    :return: warped image, transformation matrix
    """
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Contour of maximum area
    largest_contour = max(contours, key=cv2.contourArea)
    corners = get_best_fit_quad(largest_contour)
    # cv2.imwrite("hull.jpg", cv2.drawContours(img, [np.array(best_points)], 0, 255, 2))

    # rect = cv2.minAreaRect(largest_contour)
    # box = cv2.boxPoints(rect)
    # corners = np.int0(box)
    corners = corners.reshape(corners.shape[0], 2).astype(np.int32)
    corners = cyclic_intersection_pts(np.array(corners))
    # Get rotated rect dimensions
    dstPts = [[0, 0], [Config.maze_width, 0], [Config.maze_width, Config.maze_height], [0, Config.maze_height]]
    corners[0] -= buffer
    corners[1] = [corners[1][0] + buffer, corners[1][1] - buffer]
    corners[2] += buffer
    corners[3] = [corners[3][0] - buffer, corners[3][1] + buffer]
    # Get the transform
    m = cv2.getPerspectiveTransform(np.float32(corners), np.float32(dstPts))
    # Transform the image
    out = cv2.warpPerspective(img, m, (int(Config.maze_width), int(Config.maze_height)))
    # Save the output
    return out, m


def warp_image_saved_matrix(img, m):
    """
    warps an image using a transformation matrix
    :param img: image to warp
    :param m: the transformation matrix
    :return: warped image
    """
    out = cv2.warpPerspective(img, m, (int(Config.maze_width), int(Config.maze_height)))
    return out



def threshold_image(img):
    """
    thresholds an image with a maze and returns the image and the mask for the maze
    :param img: image to threshold
    :return: numpy array (thresholded image), numpy array (mask)
    """

    blur = cv2.medianBlur(img, 15)
    # img, value to give thresh, type of adaptive, type of thresh, block size (bigger takes more into account)
    # which means less sensitive in specific areas, subtracted from mean used to fine tune
    thresh = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_MEAN_C,\
        cv2.THRESH_BINARY, 2501, -22)

    # Threshold and morph close
    thresh_with_lines = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    # Contour of maximum area
    largest_contour = max(contours, key=cv2.contourArea)
    # Create a mask from the largest contour
    mask = np.zeros_like(thresh)
    cv2.drawContours(mask, [largest_contour], 0, 255, -1)
    final_thresh = np.zeros(thresh_with_lines.shape)
    final_thresh[np.logical_and(mask == 255, thresh_with_lines == 0)] = 255
    return final_thresh, mask


def fill_aruco(image, corners, extra=5):
    """
    fills the aruco on the image with the value 255
    :param image: Image to fill aruco on
    :param corners: corners of the aruco
    :param extra: extra padding to fill
    :return: new numpy array (image) that contains filled aruco
    """
    minc = min(corners, key=lambda x: x[0] + x[1])
    maxc = max(corners, key=lambda x: x[0] + x[1])
    return cv2.rectangle(image, ((int)(minc[0]) - extra, (int)(minc[1]) - extra),
                         ((int)(maxc[0]) + extra, (int)(maxc[1]) + extra), 255, -1)


def skeletonize_image(image):
    """
    skeletonizes the image
    :param image: image to skeletonize
    :return: new numpy array after skeletonizing
    """
    image = np.copy(image)
    image[image != 0] = 1
    image = skeletonize(image).astype(int)
    image[image != 0] = MAZE_COLOR
    return image


def load_image_post_aruco(im):
    """
    image processing stage after extracting aruco information.
    warps image and returns transformation matrix
    :param im: image to process
    :return: numpy array (warped), numpy array (warped without thresholding), numpy array (transformation matrix)
    """
    print("1.1")
    thresh, mask = threshold_image(im)
    cv2.imwrite("thresh.jpg", thresh)
    cv2.imwrite("mask.jpg", mask)
    print("1.2")
    warped, m = warp_image(thresh, mask)
    print("1.3")
    warped = skeletonize_image(warped).astype(np.uint8)
    print("1.4")
    warped_original = warp_image_saved_matrix(im, m)
    cv2.imwrite("warped-convex.jpg", warped_original)
    return warped, warped_original, m


class ArucoData(object):
    def __init__(self, img, aruco_dict):
        self.aruco_dict = aruco_dict
        self.aruco_info = {}
        self.extract_basic_info(img)

    def extract_basic_info(self, img):
        """
        extracts information about all aruCo in image
        :param img: image to extract information from
        :return: None
        """
        # TODO check if can use the commented lines
        dictionary = cv2.aruco.getPredefinedDictionary(self.aruco_dict)
        # parameters = cv2.aruco.DetectorParameters()  # PC
        # parameters.useAruco3Detection = True
        # detector = cv2.aruco.ArucoDetector(dictionary, parameters)  # PC
        markerCorners, markerIds, rejectedCandidates = cv2.aruco.detectMarkers(img, dictionary)  # RPI
        # markerCorners, markerIds, rejectedCandidates = detector.detectMarkers(img) # PC
        # Detect the ArUco markers in the image
        for index, id in enumerate(markerIds):
            marker_corners = markerCorners[index][0]
            center_x = int((marker_corners[0][0] + marker_corners[3][0]
                            + marker_corners[1][0] + marker_corners[2][0]) / 4)
            center_y = int((marker_corners[0][1] + marker_corners[3][1] +
                            marker_corners[2][1] + marker_corners[1][1]) / 4)
            p1, p2 = marker_corners[0], marker_corners[1]
            angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0])) % 360
            self.aruco_info[id[0]] = {"corners": marker_corners,
                                      "centerX": center_x,
                                      "centerY": center_y,
                                      "rotation": float(angle),
                                      }
        self.aruco_info[Config.CAR_ID] = {"corners": [],
                                          "centerX": self.aruco_info[Config.BACKWARD_CAR_ID]['centerX'],
                                          "centerY": self.aruco_info[Config.BACKWARD_CAR_ID]['centerY'],
                                          "rotation": 0,
                                          }


class MazeImage(object):
    """
    class that provides an interface to information regarding the maze
    """
    def __init__(self, aruco_dict=cv2.aruco.DICT_4X4_50):
        """
        :param aruco_dict: aruco dict to use for detection
        """
        self.aruco_dict = aruco_dict
        self.data, warped_orig, self.warp_matrix = None, None, None
        self.original_image = None
        self.aruco = None
        self.warped_image = None

    def load_initial_image(self, img):
        """
        loads initial image that contains only the maze
        :param img: image to process
        :return: None
        """
        print("here")
        self.data, warped_orig, self.warp_matrix = load_image_post_aruco(img)
        self.original_image = np.copy(self.data)
        self.aruco = None

    def load_aruco_image(self, img):
        """
        loads image with aruCo, warps and extracts aruCo information
        :param img:
        :return: None
        """
        data = warp_image_saved_matrix(img, self.warp_matrix)
        self.warped_image = np.copy(data)
        self.aruco = ArucoData(data, self.aruco_dict)
        self.data = np.copy(self.original_image)
        # fills out the end aruCo to compensate for the need for accurate placing
        fill_aruco(self.data, self.aruco.aruco_info[Config.END_ID]['corners'])

    def get_warped_image(self):
        return self.warped_image

    def get_car_angle(self):
        return self.aruco.aruco_info[Config.CAR_ID]['rotation']

    def is_on_maze(self, row, col):
        # checks if cord is on maze
        return self.data[row][col] == MAZE_COLOR

    def get_max_row(self):
        return self.data.shape[0]

    def get_max_col(self):
        return self.data.shape[1]

    def get_data(self):
        """
        retrieves the current image used for information retrieval
        :return: numpy array
        """
        return self.data

    def get_end_point(self):
        # returns the maze endpoint in col, row form
        return self.aruco.aruco_info[Config.END_ID]['centerY'], self.aruco.aruco_info[Config.END_ID]['centerX']

    def get_start_point(self):
        """
        runs BFS from the car's center to find closest point on maze to start movement from
        :return: None
        """

        curr_row, curr_col = self.get_current_point()
        checked = []
        q = [(curr_row, curr_col)]
        while q:
            v = q.pop(0)
            if v not in checked:
                checked.append(v)
                if 0 <= v[0] < self.original_image.shape[0] \
                        and 0 <= v[1] < self.original_image.shape[1] \
                        and self.original_image[v[0]][v[1]] == MAZE_COLOR:
                    return v
                if (v[0], v[1] - 1) not in checked:
                    q.append((v[0], v[1] - 1))
                if (v[0] + 1, v[1]) not in checked:
                    q.append((v[0] + 1, v[1]))
                if (v[0], v[1] + 1) not in checked:
                    q.append((v[0], v[1] + 1))
                if (v[0] - 1, v[1]) not in checked:
                    q.append((v[0] - 1, v[1]))
        return self.get_current_point()

    def get_current_point(self):
        """
        gets the current location of the car
        :return: (row, col)
        """
        return self.aruco.aruco_info[Config.CAR_ID]['centerY'], self.aruco.aruco_info[Config.CAR_ID]['centerX']

    def get_forward_point(self):
        """
        gets the location of the forward aruCo on the car
        :return: (row, col)
        """
        return self.aruco.aruco_info[Config.FORWARD_CAR_ID]['centerY'], self.aruco.aruco_info[Config.FORWARD_CAR_ID][
            'centerX']

    def get_direction_vector(self):
        """
        gets the direction vector of the car. The vector that represents its forward direction
        :return: (y, x)
        """
        forward = self.aruco.aruco_info[Config.FORWARD_CAR_ID]
        backward = self.aruco.aruco_info[Config.BACKWARD_CAR_ID]

        return forward['centerY'] - backward['centerY'], forward['centerX'] - backward['centerX']

#
print("1.1")
im = cv2.imread("orig.jpg", cv2.IMREAD_GRAYSCALE)
thresh, mask = threshold_image(im)
cv2.imwrite("thresh.jpg", thresh)
cv2.imwrite("mask.jpg", mask)
print("1.2")
warped, m = warp_image(thresh, mask)
print("1.3")
warped = skeletonize_image(warped).astype(np.uint8)
print("1.4")
warped_original = warp_image_saved_matrix(im, m)
cv2.imwrite("warped-convex.jpg", warped_original)