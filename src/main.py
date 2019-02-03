from time import time

import numpy as np
from cv2 import VideoWriter, VideoWriter_fourcc, circle, LINE_AA


class PointIniter:

    def __init__(self, points, size, total_sample_count=100) -> None:
        self.total_sample_count = total_sample_count
        self.size = size
        self.points = self._normalize_points(points)
        self.point_sector = self._calculate_point_secotr()
        self.point_position_by_type, self.pint_position = self._place_pints()

    @staticmethod
    def _normalize_points(points):
        total = sum(points.values())
        return {name: (value / total) for name, value in points.items()}

    def _calculate_point_secotr(self):
        segment_start = 0
        result = {}
        for name, value in self.points.items():
            segment_end = segment_start + np.pi * 2 * value
            result[name] = (segment_start, segment_end)
            segment_start = segment_end
        return result

    def _place_pints(self):
        if min(self.points.values()) * self.total_sample_count < 1:
            raise Exception("Bad proportion, can not set position")
        position_by_name = {name: [] for name, _ in self.points.items()}
        positions_list = []
        for name, (segment_start, segment_end) in self.point_sector.items():
            for i in range(int(self.points[name] * self.total_sample_count)):
                angle = np.random.rand() * (segment_end - segment_start) + segment_start
                radius = np.random.randint(0, self.size / 2)
                position = [int(self.size / 2 + np.cos(angle) * radius), int(self.size / 2 + np.sin(angle) * radius)]
                position_by_name[name].append(position)
                positions_list.append(position)
        return position_by_name, positions_list


class PointDrawer:
    radius = 0.01
    inner_radius = 0.0065

    def __init__(self, point_by_type_position, canvas_size) -> None:
        self.canvas_size = canvas_size
        self.point_by_type_position = point_by_type_position
        self.color_by_type = self._choose_color()
        self._pixel_radius = int(self.radius * canvas_size)
        self._pixel_inner_radius = int(self.inner_radius * canvas_size)
        self._circle_center = int(canvas_size / 2)

    def _choose_color(self):
        step = 1.0 / len(self.point_by_type_position)
        out_color = [np.random.rand()]
        for i in range(len(self.point_by_type_position) - 1):
            color = out_color[-1] + step
            if color >= 1:
                color = color - 1
            out_color.append(color)
        print(out_color)

        return {
            name: self._hsv_to_rgb(out_color.pop(), 1, 1) for name in self.point_by_type_position.keys()
        }

    @staticmethod
    def _hsv_to_rgb(h, s, v):
        i = np.floor(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)

        r, g, b = {
            0: (v, t, p),
            1: (q, v, p),
            2: (p, v, t),
            3: (p, q, v),
            4: (t, p, v),
            5: (v, p, q),
        }[i % 6]
        return [int(r * 255), int(g * 255), int(b * 255)]

    def draw(self, image):
        for type_name, positions in self.point_by_type_position.items():
            color = self.color_by_type[type_name]
            for position in positions:
                circle(
                    img=image,
                    center=(int(position[0]), int(position[1])),
                    radius=int(self._pixel_radius),
                    color=(0, 0, 0),
                    thickness=-1,
                    lineType=LINE_AA
                )
                circle(
                    img=image,
                    center=(int(position[0]), int(position[1])),
                    radius=int(self._pixel_inner_radius),
                    color=color,
                    thickness=-1,
                    lineType=LINE_AA
                )

        circle(
            img=image,
            center=(self._circle_center, self._circle_center),
            radius=self._circle_center,
            color=(0, 0, 0),
            thickness=self._pixel_inner_radius,
            lineType=LINE_AA
        )


class PointMover:
    expand_power = 24
    drop_power = 20
    change_point = 0.025
    random_walk_range = np.pi / 18

    power_level = 0.005


    def __init__(self, point_positions, size) -> None:
        super().__init__()
        self.size = size
        self.point_positions = point_positions
        self.move_vector = self._init_move_vectors()
        self.center_x = size / 2
        self.center_y = size / 2
        self.speed = size * 0.005

    def _get_point_on_circle(self, x, y):
        dx = x - self.center_x
        dy = y - self.center_y
        l = self._length(dx, dy)
        if l == 0:
            l = 0.001
        dx_norm = dx / l
        dy_norm = dy / l
        return (
            self.center_x + dx_norm * self.size / 2,
            self.center_y + dy_norm * self.size / 2
        )

    def _length(self, x, y):
        return (x ** 2 + y ** 2) ** 0.5

    def _get_vectors_matrix(self):
        position_matrix = [[[] for _ in range(len(self.point_positions) + 1)] for _ in self.point_positions]
        for i in range(len(self.point_positions)):
            for j in range(i, len(self.point_positions)):
                dx = (self.point_positions[i][0] - self.point_positions[j][0]) / self.size
                dy = (self.point_positions[i][1] - self.point_positions[j][1]) / self.size
                position_matrix[i][j] = [dx, dy]
                position_matrix[j][i] = [-dx, -dy]
            circle_x, circle_y = self._get_point_on_circle(self.point_positions[i][0], self.point_positions[i][1])
            dx = (self.point_positions[i][0] - circle_x) / self.size
            dy = (self.point_positions[i][1] - circle_y) / self.size
            position_matrix[i][len(self.point_positions)] = [dx, dy]
        return position_matrix

    def _get_length_matrix(self, vector_matrix):
        return [
            [self._length(x, y) for x, y in col]
            for col in vector_matrix
        ]

    def _get_power_matrix(self, length_matrix):
        result = []
        for col in length_matrix:
            result_col = []
            for power in col:
                grow = np.exp(-(self.expand_power * (self.change_point - power)) ** 2)
                if power <= self.change_point:
                    norm = np.exp(-(self.expand_power * self.change_point) ** 2)
                    grow = (grow - norm) / (1 - norm)
                drop = np.exp(-(self.drop_power * power) ** 2)
                result_col.append(drop - grow)
            result.append(result_col)
        return result

    def _update_move_vector(self, vector_matrix, power_matrix):
        result = []
        for i in range(len(vector_matrix)):
            point_x = 0
            point_y = 0
            max_power = 0
            for j in range(len(vector_matrix) + 1):
                if i == j:
                    continue
                x, y = vector_matrix[i][j]
                l = self._length(x, y)
                if l == 0:
                    l = 0.0000001
                x = (x / l) * power_matrix[i][j]
                y = (y / l) * power_matrix[i][j]
                point_x = point_x + x
                point_y = point_y + y
                max_power = max(max_power, power_matrix[i][j])

            norm_pawer = min(self.power_level, max_power) / self.power_level
            l = self._length(point_x, point_y)
            if l == 0:
                l = 0.0001
            point_x = point_x / l
            point_y = point_y / l
            angle = np.arccos(point_x)
            if point_y < 0:
                angle = (np.pi * 2) - angle

            angle = (1 - norm_pawer)*self.move_vector[i] + norm_pawer* angle
            deviation = np.random.normal(0, self.random_walk_range * (1 - norm_pawer))
            angle = angle + deviation
            self.move_vector[i] = angle
        return result

    def _recalculate_point_position(self):
        for i in range(len(self.point_positions)):
            self.point_positions[i][0] = (self.point_positions[i][0] + np.cos(self.move_vector[i]) * self.speed)
            self.point_positions[i][1] = (self.point_positions[i][1] + np.sin(self.move_vector[i]) * self.speed)

    def update_state(self):
        vector_matrix = self._get_vectors_matrix()
        lenght_matrix = self._get_length_matrix(vector_matrix)
        power = self._get_power_matrix(lenght_matrix)
        self._update_move_vector(vector_matrix, power)
        self._recalculate_point_position()

    def _init_move_vectors(self):
        return [
            np.random.rand()*2*np.pi
            for _ in self.point_positions
        ]


class GradientDrawer:
    gradient_power = 3
    bright_fix = 2

    def __init__(self, point_map_by_postion, point_color_by_type, size) -> None:
        super().__init__()
        self.point_color_by_type = point_color_by_type
        self.size = size
        self.x = np.array([i % size for i in range(size ** 2)])
        self.y = np.array([int(i / size) for i in range(size ** 2)])
        self.point_map_by_postion = point_map_by_postion
        self.max_distance = np.sqrt((self.size ** 2) * 2)
        self.mask = (
            (np.sqrt(np.power(self.x - size / 2, 2) + np.power(self.y - size / 2, 2)) > (size / 2)).
                reshape((self.size, self.size,))
        )

    def get_frame(self):
        points = []
        points_by_name = {}
        for name, points_position in self.point_map_by_postion.items():
            points_by_name[name] = []
            for point_x, point_y in points_position:
                disance = np.sqrt(np.power(self.x - point_x, 2) + np.power(self.y - point_y, 2))
                points_by_name[name].append(len(points))
                points.append(disance)
        max_d = max([np.max(p) for p in points])
        for i in range(len(points)):
            points[i] /= max_d
            points[i] = np.exp(-np.power(self.gradient_power * points[i], 2))

        result_r = np.zeros(self.size ** 2)
        result_b = np.zeros(self.size ** 2)
        result_g = np.zeros(self.size ** 2)
        for name, (r, g, b) in self.point_color_by_type.items():
            for position in points_by_name[name]:
                result_r += (points[position] * r)
                result_g += (points[position] * g)
                result_b += (points[position] * b)

        result_r /= (len(points))
        result_g /= (len(points))
        result_b /= (len(points))

        result_r *= self.bright_fix
        result_g *= self.bright_fix
        result_b *= self.bright_fix

        result_r[result_r > 255] = 255
        result_g[result_g > 255] = 255
        result_b[result_b > 255] = 255

        result_r = result_r.astype('uint8').reshape((self.size, self.size,))
        result_g = result_g.astype('uint8').reshape((self.size, self.size,))
        result_b = result_b.astype('uint8').reshape((self.size, self.size,))

        result = np.ones((self.size, self.size, 3), dtype=np.uint8) * 255
        result[:, :, 0] = result_r
        result[:, :, 1] = result_g
        result[:, :, 2] = result_b

        result[self.mask, :] = 255
        return result


if __name__ == "__main__":
    print("hello")
    width = 420
    height = width
    FPS = 25
    seconds = 25
    points = {
        'A': 1,
        'B': 1,
        'C': 2,
        'D': 3,
        'D1': 2,
        'D2': 1,
    }
    point_info = PointIniter(points, width, total_sample_count=60)
    point_draw = PointDrawer(point_info.point_position_by_type, width)
    point_mover = PointMover(point_info.pint_position, width)
    gradient_drawer = GradientDrawer(point_info.point_position_by_type, point_draw.color_by_type, width)

    print("start :: ", time())
    fourcc = VideoWriter_fourcc(*'FMP4')
    video = VideoWriter('/data/output.mp4', fourcc, float(FPS), (width, height))

    # Needed for left traces. When uncomment it,please comment `frame = gradient_drawer.get_frame()`
    # frame = np.ones((height, width, 3), dtype=np.uint8) * 255
    for frame_number in range(FPS * seconds):
        frame = gradient_drawer.get_frame()
        point_draw.draw(frame)
        video.write(frame)
        point_mover.update_state()
        print(f"frame number :: {frame_number}")
    video.release()

    print("end :: ", time())
