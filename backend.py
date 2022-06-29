"""
Backend

This file contains supplementary methods and classes applied to the frontend.

1. Class MPLCanvas: configuration of the plot canvas
2. Analysis methods: methods to process and analyze balance signals data
3. Database methods: methods of the database operations
4. About class and method: Dialogs of information about me and Qt

"""

from turtle import width
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSettings

import sys
import numpy as np
import pandas as pd
from collections import OrderedDict

from scipy.spatial import ConvexHull
import psycopg2
import cv2
import pytesseract
from pytesseract import Output

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import material3_components as mt3

light = {
    'surface': '#B2B2B2',
    'on_surface': '#000000'
}

dark = {
    'surface': '#2E3441',
    'on_surface': '#E5E9F0'
}

class MPLCanvas(FigureCanvasQTAgg):
    def __init__(self, parent, theme: bool) -> None:
        """ Canvas settings for plotting signals """
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)

        FigureCanvasQTAgg.__init__(self, self.fig)
        self.setParent(parent)

        self.apply_styleSheet(theme)

    def apply_styleSheet(self, theme):
        self.fig.subplots_adjust(left=0.05, bottom=0.15, right=1, top=0.95, wspace=0, hspace=0)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.spines['bottom'].set_visible(False)
        self.axes.spines['left'].set_visible(False)
        if theme:
            self.fig.set_facecolor(f'{light["surface"]}')
            self.axes.set_facecolor(f'{light["surface"]}')
            self.axes.xaxis.label.set_color(f'{light["on_surface"]}')
            self.axes.yaxis.label.set_color(f'{light["on_surface"]}')
            self.axes.tick_params(axis='both', colors=f'{light["on_surface"]}', labelsize=8)
        else:
            self.fig.set_facecolor(f'{dark["surface"]}')
            self.axes.set_facecolor(f'{dark["surface"]}')
            self.axes.xaxis.label.set_color(f'{dark["on_surface"]}')
            self.axes.yaxis.label.set_color(f'{dark["on_surface"]}')
            self.axes.tick_params(axis='both', colors=f'{dark["on_surface"]}', labelsize=8)

# ----------------------
# Extracción de la Señal
# ----------------------
def convert_cv_qt(cv_img):
    """Convert from an opencv image to QPixmap"""
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
    p = convert_to_Qt_format.scaled(1280, 720, Qt.AspectRatioMode.KeepAspectRatio)
    return QPixmap.fromImage(p)


def image_ocr(image):
    """ Extract text from image """
    pytesseract.pytesseract.tesseract_cmd = 'C:/Tesseract-OCR/tesseract.exe'
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    image_data = cv2.findNonZero(image)
    image_data = sorted(image_data , key=lambda k: [k[0][0], k[0][1]])
    x, y = [], []
    for element in image_data:
        x.append(element[0][0])
        y.append(element[0][1])

    df_x = pd.DataFrame(x)
    df_y = pd.DataFrame(y)

    x_min = int(df_x.min())
    x_max = int(df_x.max())
    y_min = int(df_y.min())
    y_max = int(df_y.max())

    fx=5
    ap_max_image = image[y_min-2:y_min+9 , x_min:x_max]
    ap_max_image = cv2.resize(ap_max_image, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
    ret, ap_max_image = cv2.threshold(ap_max_image, 250, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    ap_min_image = image[y_max-9:y_max+2 , x_min:x_max]
    ap_min_image = cv2.resize(ap_min_image, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
    ret, ap_min_image = cv2.threshold(ap_min_image, 250, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    
    lat_min_image = image[y_min:y_max , x_min-2:x_min+9]
    lat_min_image = cv2.rotate(lat_min_image, cv2.ROTATE_90_CLOCKWISE)
    lat_min_image = cv2.resize(lat_min_image, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
    ret, lat_min_image = cv2.threshold(lat_min_image, 250, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    
    lat_max_image = image[y_min:y_max , x_max-9:x_max+2]
    lat_max_image = cv2.rotate(lat_max_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    lat_max_image = cv2.resize(lat_max_image, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
    ret, lat_max_image = cv2.threshold(lat_max_image, 250, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    ap_max_text = float(pytesseract.image_to_string(ap_max_image, config='--psm 7 -c tessedit_char_whitelist=0123456789-.m')[:-3])
    ap_min_text = float(pytesseract.image_to_string(ap_min_image, config='--psm 7 -c tessedit_char_whitelist=0123456789-.m')[:-3])
    lat_min_text = float(pytesseract.image_to_string(lat_min_image, config='--psm 7 -c tessedit_char_whitelist=0123456789-.m')[:-3])
    lat_max_text = float(pytesseract.image_to_string(lat_max_image, config='--psm 7 -c tessedit_char_whitelist=0123456789-.m')[:-3])
    
    ap = ( ap_max_text , ap_min_text )
    lat = ( lat_max_text , lat_min_text )

    return ap,lat


def image_signal(image, limits):
    width = image.shape[1]
    rango = float(limits[0] - limits[1])
    data = cv2.findNonZero(image)
    data = sorted(data, key=lambda k: [k[0][0], k[0][1]])
    data = [(x[0][0], float(-x[0][1])) for x in data]

    signal = OrderedDict()
    for x, y in data:
        signal.setdefault(x, []).append(y)
    signal = [(k, sum(v) / len(v)) for k, v in signal.items()]

    temp = []
    index_signal = 0
    for i in range(width):
        if i == signal[index_signal][0]:
            temp.append((i,signal[index_signal][1]))
            index_signal += 1
        else:
            temp.append((i,np.nan))

    df_temp = pd.DataFrame(temp)
    df_temp.interpolate(method='linear', limit_direction='both', inplace=True)
    signal = list(df_temp.to_records(index=False))

    y_min = float(min(signal , key=lambda k: k[1])[1])
    signal = [(x[0], x[1] - y_min) for x in signal]
    y_max = float(max(signal , key=lambda k: k[1])[1])
    signal = [(x[0], (x[1] / y_max * rango) + limits[1]) for x in signal]

    y = pd.DataFrame(signal)[1]
    t = pd.DataFrame(signal)[0]

    return y[1:], t[1:]


def extract(image_file: str) -> pd.DataFrame:
    image = cv2.imread(image_file)

    # OCR
    image_left_limits = image.copy()
    image_left_limits = image_left_limits[ 144:315 , 108:513]
    left_ap_limits,left_lat_limits = image_ocr(image_left_limits)

    image_center_limits = image.copy()
    image_center_limits = image_center_limits[ 144:315 , 529:934]
    center_ap_limits,center_lat_limits = image_ocr(image_center_limits)

    image_right_limits = image.copy()
    image_right_limits = image_right_limits[ 144:315 , 949:1354]
    right_ap_limits,right_lat_limits = image_ocr(image_right_limits)

    # Signals
    image_left = image.copy()
    image_center = image.copy()
    image_right = image.copy()

    image_left[(image_left[:,:,0] > 0) | (image_left[:,:,1] > 0) | (image_left[:,:,2] < 255)] = 0
    image_center[(image_center[:,:,0] > 0) | (image_center[:,:,1] < 255) | (image_center[:,:,2] > 0)] = 0
    image_right[(image_right[:,:,0] < 255) | (image_right[:,:,1] > 0) | (image_right[:,:,2] > 0)] = 0

    # Lateral Signal
    left_lateral_image = image_left[ 342:498 , 127:1322 , 2 ]
    center_lateral_image = image_center[ 342:498 , 127:1322 , 1 ]
    right_lateral_image = image_right[ 342:498 , 127:1322 , 0 ]

    left_lateral_signal, left_lateral_time = image_signal(left_lateral_image, left_lat_limits)
    center_lateral_signal, center_lateral_time = image_signal(center_lateral_image, center_lat_limits)
    right_lateral_signal, right_lateral_time = image_signal(right_lateral_image, right_lat_limits)

    # Antero-Posterior Signal
    left_ap_image = image_left[ 538:694 , 127:1322 , 2 ]
    center_ap_image = image_center[ 538:694 , 127:1322 , 1 ]
    right_ap_image = image_right[ 538:694 , 127:1322 , 0 ]

    left_ap_signal, left_ap_time = image_signal(left_ap_image, left_ap_limits)
    center_ap_signal, center_ap_time = image_signal(center_ap_image, center_ap_limits)
    right_ap_signal, right_ap_time = image_signal(right_ap_image, right_ap_limits)

    signals = {
        'left_lateral_signal': left_lateral_signal,
        'left_lateral_time': left_lateral_time,
        'center_lateral_signal': center_lateral_signal,
        'center_lateral_time': center_lateral_time,
        'right_lateral_signal': right_lateral_signal,
        'right_lateral_time': right_lateral_time,
        'left_ap_signal': left_ap_signal,
        'left_ap_time': left_ap_time,
        'center_ap_signal': center_ap_signal,
        'center_ap_time': center_ap_time,
        'right_ap_signal': right_ap_signal,
        'right_ap_time': right_ap_time
        }

    return signals


# --------------------
# Análisis de la Señal
# --------------------
def analisis(df: pd.DataFrame) -> dict:
    """ Analysis of dataframe from balance signal

    Parameters
    ----------
    df: pd.DataFrame
        Pandas dataframe converted from balance signal data from file
    
    Returns
    -------
    results: dict
        Results of dataframe analysis of lateral, antero-posterior, and
        center of pressure oscillations
        data_x: pd.DataFrame
            Lateral signal
        data_y: pd.DataFrame
            Antero-posterior signal
        data_t: 
            Time signal
        lat_max: float
            Lateral signal maximum value
        lat_t_max: float
            Lateral signal correspondent time value for maximum value
        lat_min: float
            Lateral signal minimum value
        lat_t_min: float
            Lateral signal correspondent time value for minimum value
        ap_max: float
            Antero-posterior signal maximum value
        ap_t_max: float
            Antero-posterior signal correspondent time value for maximum value
        ap_min: float
            Antero-posterior signal minimum value
        ap_t_min: float
            Antero-posterior signal correspondent time value for minimum value
        lat_rango: float
            Lateral signal range
        ap_rango: float
            Antero-posterior signal range
        lat_vel: float
            Lateral signal mean velocity
        lat_rms: float
            Lateral signal RMS
        ap_vel: float
            Antero-posterior signal mean velocity
        ap_rms: float
            Antero-posterior signal RMS
        centro_vel: float
            Center of pressure signal mean velocity
        centro_dist: float
            Center of pressure signal mean distance
        centro_frec: float
            Center of pressure signal mean frequency
    """
    results = {}

    data_x = df.iloc[:,0]
    data_y = df.iloc[:,1]
    data_t = np.linspace(0, len(df) / 10, len(df))

    results['data_x'] = data_x
    results['data_y'] = data_y
    results['data_t'] = data_t

    x_max = data_x.max()
    x_min = data_x.min()
    y_max = data_y.max()
    y_min = data_y.min()

    results['lat_max'] = x_max
    results['lat_t_max'] = data_x.idxmax() / 10
    results['lat_min'] = x_min
    results['lat_t_min'] = data_x.idxmin() / 10

    results['ap_max'] = y_max
    results['ap_t_max'] = data_y.idxmax() / 10
    results['ap_min'] = y_min
    results['ap_t_min'] = data_y.idxmin() / 10

    results['lat_rango'] = x_max - x_min
    results['ap_rango'] = y_max - y_min

    tAnalisis = len(df) / 10
    time_analysis = len(df) - 1
    den = tAnalisis / len(df)

    # SEÑAL X ----------------------------------------------------------------
    avgX = data_x.sum() / len(df)

    numX = abs(data_x.diff()).dropna()
    velSgnX = numX / den
    results['lat_vel'] = velSgnX.sum() / time_analysis

    numRMSX = (data_x - avgX) * (data_x - avgX)
    results['lat_rms'] = np.sqrt(numRMSX.sum() / time_analysis)
    
    # SEÑAL Y ----------------------------------------------------------------
    avgY = data_y.sum() / len(df)

    numY = abs(data_y.diff()).dropna()
    velSgnY = numY / den
    results['ap_vel'] = velSgnY.sum() / time_analysis

    numRMSY = (data_y - avgY) * (data_y - avgY)
    results['ap_rms'] = np.sqrt(numRMSY.sum() / time_analysis)

    # SEÑALES X Y ------------------------------------------------------------
    num2 = np.sqrt((numX * numX) + (numY * numY))
    numVMT = num2 / tAnalisis
    results['centro_vel'] = numVMT.sum()

    numDist = np.sqrt((data_x * data_x) + (data_y * data_y))
    distM = numDist / tAnalisis

    results['centro_dist'] = distM.sum()
    results['centro_frec'] = numVMT.sum() / (2 * np.pi)

    return results


# ------
# Elipse
# ------
def ellipseStandard(df: pd.DataFrame) -> dict:
    """ Ellipse analysis of dataframe from balance signal

    Parameters
    ----------
    df: pd.DataFrame
        Pandas dataframe converted from balance signal data from file
    
    Returns
    -------
    results: dict
        Results of ellipse clustering analysis
        x: list
            x-coordinates of ellipse points
        y: list
            y-coordinates of ellipse points
        area: float
            area of ellipse
    """
    data_x = df.iloc[:,0]
    data_y = df.iloc[:,1]

    x_max = data_x.max()
    x_min = data_x.min()
    y_max = data_y.max()
    y_min = data_y.min()

    a = (x_max - x_min) / 2
    b = (y_max - y_min) / 2
    x0 = x_max - a
    y0 = y_max - b

    theta = np.linspace(0, 2 * np.pi, 100)
    x = x0 + a * np.cos(theta)
    y = y0 + b * np.sin(theta)

    results = {
        'x': x,
        'y': y,
        'area': np.pi * a * b
    }

    return results


# -----------
# Convex Hull
# -----------
def convexHull(df: pd.DataFrame) -> dict:
    """ Convex hull analysis of dataframe from balance signal

    Parameters
    ----------
    df: pd.DataFrame
        Pandas dataframe converted from balance signal data from file
    
    Returns
    -------
    results: dict
        Results of convex hull clustering analysis
        x: list
            x-coordinates of convex hull points
        y: list
            y-coordinates of convex hull points
        area: float
            area of convex hull
    """
    data_x = df.iloc[:,0]
    data_y = df.iloc[:,1]
    data = np.stack((data_x.to_numpy(), data_y.to_numpy()), axis=1)

    hull = ConvexHull(data)
    hullX = data[hull.vertices, 0]
    hullY = data[hull.vertices, 1]

    results = {
        'x': hullX,
        'y': hullY,
        'area': hull.volume # 2D Area
    }

    return results


# ----------------
# Elipse Orientada
# ----------------
def ellipsePCA(df: pd.DataFrame) -> dict:
    """ Oriented ellipse analysis of dataframe from balance signal

    Parameters
    ----------
    df: pd.DataFrame
        Pandas dataframe converted from balance signal data from file
    
    Returns
    -------
    results: dict
        Results of oriented ellipse clustering analysis
        x: list
            x-coordinates of oriented ellipse points
        y: list
            y-coordinates of oriented ellipse points
        area: float
            area of oriented ellipse
    """
    data_x = df.iloc[:,0]
    data_y = df.iloc[:,1]

    sumX = data_x.sum()
    sumY = data_y.sum()
    cen = ( sumX / len(df) , sumY / len(df) )

    covXX = (data_x - cen[0]) * (data_x - cen[0])
    covXY = (data_x - cen[0]) * (data_y - cen[1])
    covYY = (data_y - cen[1]) * (data_y - cen[1])
    JX = data_x - cen[0]
    JY = data_y - cen[1]
    theta = np.arctan2(JY , JX)
    rho = np.sqrt((JX * JX) + (JY * JY))

    a = covXX.sum() / len(covXX)
    b = covXY.sum() / len(covXY)
    d = covYY.sum() / len(covYY)

    B = a + d
    C = a * d - b * b
    L1 = (B / 2) + np.sqrt(B * B - 4 * C) / 2
    eigvec = ( L1 - d , b )

    rot = np.arctan( (L1 - d) / b )

    thetarot = theta + rot
    rotX = rho * np.cos(thetarot)
    rotY = rho * np.sin(thetarot)

    maxX = rotX.max()
    minX = rotX.min()
    maxY = rotY.max()
    minY = rotY.min()

    aa = (maxX - minX) / 2
    bb = (maxY - minY) / 2
    x0 = maxX - aa
    y0 = maxY - bb

    phi = np.linspace(0, 2 * np.pi, 100)
    newX = x0 + aa * np.cos(phi)
    newY = y0 + bb * np.sin(phi)
    thetaellipse = np.arctan2(newY, newX)
    rhoellipse = np.sqrt((newX * newX) + (newY * newY))
    thetarotellipse = thetaellipse - rot
    Xellipse = rhoellipse * np.cos(thetarotellipse)
    Yellipse = rhoellipse * np.sin(thetarotellipse)
    XellipseFinal = Xellipse + cen[0]
    YellipseFinal = Yellipse + cen[1]

    results = {
        'x': XellipseFinal,
        'y': YellipseFinal,
        'area': np.pi * aa * bb
    }

    return results

# ---------
# Funciones
# ---------
def create_db(db_table: str) -> list:
    """ Creates database tables if they don't exist and returns table data
    
    Parameters
    ----------
    db_table: str
        Database table name
    
    Returns
    -------
    table_data: list
        Data of table if exists (empty if table don't exist)
    """
    settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
    db_host = settings.value('db_host')
    db_port = settings.value('db_port')
    db_name = settings.value('db_name')
    db_user = settings.value('db_user')
    db_password = settings.value('db_password')
    try:
        connection = psycopg2.connect(user=db_user, 
                                  password=db_password, 
                                  host=db_host, 
                                  port=db_port, 
                                  database=db_name)
    except psycopg2.OperationalError as err:
        return err

    cursor = connection.cursor()

    if db_table == 'pacientes':
        cursor.execute("""CREATE TABLE IF NOT EXISTS pacientes (
                        id serial PRIMARY KEY,
                        last_name VARCHAR(128) NOT NULL,
                        first_name VARCHAR(128) NOT NULL,
                        id_type CHAR(2) NOT NULL,
                        id_number BIGINT UNIQUE NOT NULL,
                        birth_date VARCHAR(128) NOT NULL,
                        sex CHAR(1) NOT NULL,
                        weight NUMERIC(5,2) NOT NULL,
                        weight_unit CHAR(2) NOT NULL,
                        height NUMERIC(3,2) NOT NULL,
                        height_unit VARCHAR(7) NOT NULL,
                        bmi NUMERIC(4,2) NOT NULL
                        )""")
    elif db_table == 'estudios':
        cursor.execute("""CREATE TABLE IF NOT EXISTS estudios (
                        id serial PRIMARY KEY,
                        id_number BIGINT NOT NULL,
                        file_name VARCHAR(128) UNIQUE NOT NULL,
                        file_path VARCHAR(128) UNIQUE NOT NULL
                        )""")

    connection.commit()

    table_data = None
    if db_table == 'pacientes':
        cursor.execute('SELECT * FROM pacientes ORDER BY id ASC')
        table_data = cursor.fetchall()
    
    connection.close()

    return table_data


def add_db(db_table: str, data: dict) -> list:
    """ Adds data to database table and returns table data updated
    
    Parameters
    ----------
    db_table: str
        Database table name
    data: dict
        Data from patient or study file
    
    Returns
    -------
    table_data: list
        Data of table updated
    """
    if db_table == 'pacientes':
        last_name_value = data['last_name']
        first_name_value = data['first_name']
        id_type_value = data['id_type']
        id_value = data['id']
        birth_date_value = data['birth_date']
        sex_value = data['sex']
        weight_value = data['weight']
        weight_unit = data['weight_unit']
        height_value = data['height']
        height_unit = data['height_unit']
        bmi_value = data['bmi']
    elif db_table == 'estudios':
        id_value = data['id_number']
        file_name_value = data['file_name']
        file_path_value = data['file_path']

    settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
    db_host = settings.value('db_host')
    db_port = settings.value('db_port')
    db_name = settings.value('db_name')
    db_user = settings.value('db_user')
    db_password = settings.value('db_password')
    connection = psycopg2.connect(user=db_user, 
                                  password=db_password, 
                                  host=db_host, 
                                  port=db_port, 
                                  database=db_name)
    cursor = connection.cursor()

    insert_query = None
    if db_table == 'pacientes':
        insert_query = f"""INSERT INTO pacientes (last_name, first_name, id_type, id_number, birth_date, sex, weight, weight_unit, height, height_unit, bmi) 
                    VALUES ('{last_name_value}', '{first_name_value}', '{id_type_value}', '{id_value}', '{birth_date_value}', '{sex_value}', '{weight_value}', '{weight_unit}', '{height_value}', '{height_unit}', '{bmi_value}')"""
    elif db_table == 'estudios':
        insert_query = f"""INSERT INTO estudios (id_number, file_name, file_path) 
                    VALUES ('{id_value}', '{file_name_value}', '{file_path_value}')"""

    cursor.execute(insert_query)
    connection.commit()

    table_data = None
    if db_table == 'pacientes':
        cursor.execute('SELECT * FROM pacientes ORDER BY id ASC')
        table_data = cursor.fetchall()
    elif db_table == 'estudios':
        cursor.execute(f"SELECT * FROM estudios WHERE id_number='{id_value}' ORDER BY id ASC")
        table_data = cursor.fetchall()
    
    connection.close()

    return table_data


def get_db(db_table: str, data_id: str) -> list:
    """ Get data from database table
    
    Parameters
    ----------
    db_table: str
        Database table name
    data_id: str
        Patient id number
    
    Returns
    -------
    table_data: list
        Data of table
    """
    settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
    db_host = settings.value('db_host')
    db_port = settings.value('db_port')
    db_name = settings.value('db_name')
    db_user = settings.value('db_user')
    db_password = settings.value('db_password')
    connection = psycopg2.connect(user=db_user, 
                                  password=db_password, 
                                  host=db_host, 
                                  port=db_port, 
                                  database=db_name)
    cursor = connection.cursor()

    table_data = None
    if db_table == 'pacientes':
        cursor.execute(f"SELECT * FROM pacientes WHERE id_number='{data_id}'")
    elif db_table == 'estudios':
        cursor.execute(f"SELECT * FROM estudios WHERE id_number='{data_id}'")
    table_data = cursor.fetchall()
    connection.close()
    
    return table_data


def edit_db(db_table: str, id_db: int, data: dict) -> list:
    """ Edit data of a database table and returns table data updated
    
    Parameters
    ----------
    db_table: str
        Database table name
    id_db: int
        Database item id from table
    data: dict
        Data from patient or study file
    
    Returns
    -------
    table_data: list
        Data of table updated
    """
    if db_table == 'pacientes':
        last_name_value = data['last_name']
        first_name_value = data['first_name']
        id_type_value = data['id_type']
        id_value = data['id']
        birth_date_value = data['birth_date']
        sex_value = data['sex']
        weight_value = data['weight']
        weight_unit = data['weight_unit']
        height_value = data['height']
        height_unit = data['height_unit']
        bmi_value = data['bmi']
    elif db_table == 'estudios':
        id_value = data['id']
        file_name_value = data['file_name']
        file_path_value = data['file_path']

    settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
    db_host = settings.value('db_host')
    db_port = settings.value('db_port')
    db_name = settings.value('db_name')
    db_user = settings.value('db_user')
    db_password = settings.value('db_password')
    connection = psycopg2.connect(user=db_user, 
                                  password=db_password, 
                                  host=db_host, 
                                  port=db_port, 
                                  database=db_name)
    cursor = connection.cursor()    
    
    update_query = None
    if db_table == 'pacientes':
        update_query = f"""UPDATE pacientes 
                    SET (last_name, first_name, id_type, id_number, birth_date, sex, weight, weight_unit, height, height_unit, bmi)
                    = ('{last_name_value}', '{first_name_value}', '{id_type_value}', '{id_value}', '{birth_date_value}', '{sex_value}', '{weight_value}', '{weight_unit}', '{height_value}', '{height_unit}', '{bmi_value}') 
                    WHERE id = '{id_db}' """
    elif db_table == 'estudios':
        update_query = f"""UPDATE estudios 
                    SET (id_number, file_name, file_path)
                    = ('{id_value}', '{file_name_value}', '{file_path_value}') 
                    WHERE id = '{id_db}' """
    
    cursor.execute(update_query)
    connection.commit()

    table_data = None
    if db_table == 'pacientes':
        cursor.execute('SELECT * FROM pacientes ORDER BY id ASC')
        table_data = cursor.fetchall()
    elif db_table == 'estudios':
        cursor.execute('SELECT * FROM estudios')
        table_data = cursor.fetchall()
    
    connection.close()

    return table_data


def delete_db(db_table: str, data: str) -> list:
    """ Delete data from database table and returns table data updated
    
    Parameters
    ----------
    db_table: str
        Database table name
    data: str
        From patient: id number
        From study: study file
    
    Returns
    -------
    table_data: list
        Data of table updated
    """
    settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
    db_host = settings.value('db_host')
    db_port = settings.value('db_port')
    db_name = settings.value('db_name')
    db_user = settings.value('db_user')
    db_password = settings.value('db_password')
    connection = psycopg2.connect(user=db_user, 
                                  password=db_password, 
                                  host=db_host, 
                                  port=db_port, 
                                  database=db_name)
    cursor = connection.cursor()

    delete_query = None
    if db_table == 'pacientes':
        delete_query = f"DELETE FROM pacientes WHERE id_number='{data}'"
    elif db_table == 'estudios':
        delete_query = f"DELETE FROM estudios WHERE file_name='{data}'"
    cursor.execute(delete_query)
    connection.commit()

    table_data = None
    if db_table == 'pacientes':
        cursor.execute('SELECT * FROM pacientes ORDER BY id ASC')
        table_data = cursor.fetchall()
    elif db_table == 'estudios':
        cursor.execute('SELECT * FROM estudios')
        table_data = cursor.fetchall()
    
    connection.close()

    return table_data


# ----------------
# About App Dialog
# ----------------
class AboutApp(QtWidgets.QDialog):
    def __init__(self) -> None:
        """ About Me Dialog """
        super().__init__()
        # --------
        # Settings
        # --------
        self.settings = QSettings(f'{sys.path[0]}/settings.ini', QSettings.Format.IniFormat)
        self.language_value = int(self.settings.value('language'))
        self.theme_value = eval(self.settings.value('theme'))

        # ----------------
        # Generación de UI
        # ----------------
        width = 320
        height = 408
        screen_x = int(self.screen().availableGeometry().width() / 2 - (width / 2))
        screen_y = int(self.screen().availableGeometry().height() / 2 - (height / 2))

        if self.language_value == 0:
            self.setWindowTitle('Acerca de...')
        elif self.language_value == 1:
            self.setWindowTitle('About...')
        self.setGeometry(screen_x, screen_y, width, height)
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setModal(True)
        self.setObjectName('object_about')
        if self.theme_value:
            self.setStyleSheet(f'QWidget#object_about {{ background-color: #E5E9F0;'
                f'color: #000000 }}')
        else:
            self.setStyleSheet(f'QWidget#object_about {{ background-color: #3B4253;'
                f'color: #E5E9F0 }}')


        self.about_card = mt3.Card(self, 'about_card',
            (8, 8, width-16, height-16), ('Estabilometría', 'Stabilometry'), 
            self.theme_value, self.language_value)

        y, w = 48, width - 32
        mt3.FieldLabel(self.about_card, 'version_label',
            (8, y), ('Versión: 1.0', 'Version: 1.0'), self.theme_value, self.language_value)

        y += 48
        mt3.FieldLabel(self.about_card, 'desarrollado_label',
            (8, y), ('Desarrollado por:', 'Developed by:'), self.theme_value, self.language_value)

        y += 48
        mt3.IconLabel(self.about_card, 'nombre_icon',
            (8, y), 'person', self.theme_value)

        y += 6
        mt3.FieldLabel(self.about_card, 'nombre_label',
            (48, y), ('Carlos Andrés Wilches Pérez', 'Carlos Andrés Wilches Pérez'), self.theme_value, self.language_value)

        y += 30
        mt3.IconLabel(self.about_card, 'profesion_icon',
            (8, y), 'school', self.theme_value)
        
        y += 6
        mt3.FieldLabel(self.about_card, 'profesion_label',
            (48, y), ('Ingeniero Electrónico, BSc. MSc. PhD.', 'Electronic Engineer, BSc. MSc. PhD.'), self.theme_value, self.language_value)
        
        y += 24
        mt3.FieldLabel(self.about_card, 'profesion_label',
            (48, y), ('Universidad Nacional de Colombia', 'Universidad Nacional de Colombia'), self.theme_value, self.language_value)

        y += 32
        mt3.FieldLabel(self.about_card, 'profesion_label',
            (48, y), ('Maestría en Ingeniería Electrónica', 'Master in Electronic Engineering'), self.theme_value, self.language_value)

        y += 24
        mt3.FieldLabel(self.about_card, 'profesion_label',
            (48, y), ('Doctor en Ingeniería', 'Doctor in Engineering'), self.theme_value, self.language_value)

        y += 24
        mt3.FieldLabel(self.about_card, 'profesion_label',
            (48, y), ('Pontificia Universidad Javeriana', 'Pontificia Universidad Javeriana'), self.theme_value, self.language_value)

        y += 24
        mt3.IconLabel(self.about_card, 'email_icon',
            (8, y), 'mail', self.theme_value)

        y += 6
        mt3.FieldLabel(self.about_card, 'email_label',
            (48, y), ('cawilchesp@outlook.com', 'cawilchesp@outlook.com'), self.theme_value, self.language_value)

        y += 32
        self.aceptar_button = mt3.TextButton(self.about_card, 'aceptar_button',
            (w-92, y, 100), ('Aceptar', 'Ok'), 'done.png', self.theme_value, self.language_value)
        self.aceptar_button.clicked.connect(self.on_aceptar_button_clicked)

    def on_aceptar_button_clicked(self):
        self.close()

# ---------------
# About Qt Dialog
# ---------------
def about_qt_dialog(parent, language: int) -> None:
    """ About Qt Dialog """
    if language == 0:   title = 'Acerca de Qt...'
    elif language == 1: title = 'About Qt...'
    QtWidgets.QMessageBox.aboutQt(parent, title)