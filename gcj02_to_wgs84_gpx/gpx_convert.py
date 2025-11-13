import xml.etree.ElementTree as ET
import math
import sys
import os

# -----------------------------
#  GCJ-02 <-> WGS-84 工具函数
# -----------------------------
PI = 3.1415926535897932384626
A = 6378245.0           # Krasovsky 椭球
EE = 0.00669342162296594323

def out_of_china(lat, lon):
    """不在中国范围内就不做火星偏移"""
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)

def _transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret

def wgs84_to_gcj02(lat, lon):
    """WGS-84 -> GCJ-02"""
    if out_of_china(lat, lon):
        return lat, lon
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlon = (dlon * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    mgLat = lat + dlat
    mgLon = lon + dlon
    return mgLat, mgLon

def gcj02_to_wgs84(lat, lon, iterations=2):
    """
    GCJ-02 -> WGS-84
    用迭代反算，精度大约在 1m 左右。
    """
    if out_of_china(lat, lon):
        return lat, lon
    wgLat, wgLon = lat, lon
    for _ in range(iterations):
        mgLat, mgLon = wgs84_to_gcj02(wgLat, wgLon)
        dLat = mgLat - lat
        dLon = mgLon - lon
        wgLat -= dLat
        wgLon -= dLon
    return wgLat, wgLon

# -----------------------------
#  GPX 轨迹转换
# -----------------------------
def convert_gpx_gcj_to_wgs84(input_path, output_path):
    tree = ET.parse(input_path)
    root = tree.getroot()

    # GPX 1.1 命名空间
    ns = {'g': 'http://www.topografix.com/GPX/1/1'}

    count = 0

    # 视情况把 trkpt / rtept 都转换
    points_paths = [
        ".//g:trkpt",  # 轨迹点
        ".//g:rtept",  # 路线点
        ".//g:wpt",    # 单独航点
    ]

    for path in points_paths:
        for pt in root.findall(path, ns):
            lat = float(pt.attrib["lat"])
            lon = float(pt.attrib["lon"])
            wlat, wlon = gcj02_to_wgs84(lat, lon)
            pt.set("lat", f"{wlat:.8f}")
            pt.set("lon", f"{wlon:.8f}")
            count += 1

    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return count

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python gcj02_to_wgs84_gpx.py 输入.gpx 输出.gpx")
        sys.exit(1)

    in_file = sys.argv[1]
    out_file = sys.argv[2]

    if not os.path.exists(in_file):
        print(f"输入文件不存在: {in_file}")
        sys.exit(1)

    n = convert_gpx_gcj_to_wgs84(in_file, out_file)
    print(f"已转换 {n} 个点，输出文件: {out_file}")