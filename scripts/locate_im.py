import numpy as np
import cv2
import collections
import subprocess
import os
import datetime

Box = collections.namedtuple('Box', 'left top width height')
RGB = collections.namedtuple('RGB', 'red green blue')
# Point = collections.namedtuple('Point', 'x y')

def screenshot(image_name=None, region=None):
    """
    Captura uma captura de tela e retorna a imagem.
    
    Args:
        image_name (str, opcional): Nome do arquivo da imagem capturada. Se None, será gerado um nome automático.
        region (tuple, opcional): Região específica da tela a ser capturada no formato (x, y, largura, altura). Se None, captura a tela inteira.
    
    Returns:
        numpy.ndarray: Imagem capturada em formato OpenCV (BGR).
    """
    if image_name is None:
        tmp_filename = f"screenshot{(datetime.datetime.now().strftime('%Y-%m%d_%H-%M-%S-%f'))}.png"
    else:
        tmp_filename = image_name
    if region is None:
        subprocess.run(['screencapture', '-x', tmp_filename])
        im = cv2.imread(tmp_filename)
    else:
        subprocess.run(['screencapture', '-x', "-R", f"{region[0]//2},{region[1]//2},{region[2]//2+1},{region[3]//2+1}", tmp_filename])
        im = cv2.imread(tmp_filename)
        im = im[region[1] % 2:region[1] % 2 + region[3], region[0] % 2:region[0] % 2 + region[2], :]

    if image_name is None:
        os.unlink(tmp_filename)
    return im

def locate_all(needle_image, haystack_image, limit=10000, confidence=0.999, show=False):
    """
    Localiza todas as ocorrências de uma imagem dentro de outra.
    
    Args:
        needle_image (str ou numpy.ndarray): Caminho da imagem ou a imagem em si que será procurada.
        haystack_image (str ou numpy.ndarray): Caminho da imagem ou a imagem onde a busca será feita.
        limit (int, opcional): Número máximo de ocorrências a serem retornadas. Padrão é 10000.
        confidence (float, opcional): Nível mínimo de correspondência para considerar um match. Padrão é 0.999.
        show (bool, opcional): Se True, exibe as imagens para depuração. Padrão é False.
    
    Yields:
        Box: Coordenadas (x, y, largura, altura) das correspondências encontradas.
    """
    if type(needle_image) == str:
        needle_image = cv2.imread(needle_image)
        if needle_image is None:
            raise FileNotFoundError("Não foi possível abrir o arquivo. Verifique o caminho e a integridade da imagem.")
    if type(haystack_image) == str:
        haystack_image = cv2.imread(haystack_image)
        if haystack_image is None:
            raise FileNotFoundError("Não foi possível abrir o arquivo. Verifique o caminho e a integridade da imagem.")

    needle_height, needle_width = needle_image.shape[:2]
    from PIL import Image
    if show:
        Image._show(Image.fromarray(needle_image[:, :, -1]))
        Image._show(Image.fromarray(haystack_image[:, :, -1]))

    if (haystack_image.shape[0] < needle_image.shape[0] or haystack_image.shape[1] < needle_image.shape[1]):
        raise ValueError("Dimensões da imagem de busca são menores que a imagem a ser localizada.")

    result = cv2.matchTemplate(haystack_image, needle_image, cv2.TM_CCOEFF_NORMED)
    match_indices = np.arange(result.size)[(result > confidence).flatten()]
    matches = np.unravel_index(match_indices[:limit], result.shape)

    if len(matches[0]) == 0:
        return

    for x, y in zip(matches[1], matches[0]):
        yield Box(x, y, needle_width, needle_height)

def locate(needle_image, haystack_image, limit=10000, confidence=0.999):
    """
    Localiza a primeira ocorrência de uma imagem dentro de outra.
    
    Args:
        needle_image (str ou numpy.ndarray): Imagem ou caminho da imagem a ser localizada.
        haystack_image (str ou numpy.ndarray): Imagem ou caminho da imagem onde será feita a busca.
        limit (int, opcional): Número máximo de ocorrências a serem processadas. Padrão é 10000.
        confidence (float, opcional): Nível mínimo de correspondência para considerar um match. Padrão é 0.999.
    
    Returns:
        Box ou None: Retorna as coordenadas da primeira ocorrência ou None se não for encontrado.
    """
    results = tuple(locate_all(needle_image, haystack_image, limit, confidence))
    return results[0] if results else None

def locate_all_on_screen(im_name, region=None, confidence=0.999):
    """
    Localiza todas as ocorrências de uma imagem na tela.
    
    Args:
        im_name (str): Caminho da imagem a ser localizada.
        region (tuple, opcional): Região da tela onde procurar. Padrão é None (tela inteira).
        confidence (float, opcional): Nível mínimo de correspondência. Padrão é 0.999.
    
    Returns:
        list: Lista de Boxes com coordenadas das correspondências encontradas.
    """
    needle_image = cv2.imread(im_name)
    haystack_image = screenshot(region=region)
    relative_results = tuple(locate_all(needle_image, haystack_image, confidence=confidence))
    absolute_results = []
    if region is None:
        region = (0, 0, 0, 0)
    for result in relative_results:
        absolute_results.append(Box(result[0] + region[0], result[1] + region[1], result[2], result[3]))
    return absolute_results

def locate_on_screen(im_name, region=None, confidence=0.999):
    """
    Localiza a primeira ocorrência de uma imagem na tela.
    
    Args:
        im_name (str): Caminho da imagem a ser localizada.
        region (tuple, opcional): Região da tela onde procurar. Padrão é None (tela inteira).
        confidence (float, opcional): Nível mínimo de correspondência. Padrão é 0.999.
    
    Returns:
        Box ou None: Retorna as coordenadas da primeira ocorrência ou None se não for encontrado.
    """
    results = locate_all_on_screen(im_name, region, confidence)
    return results[0] if results else None

def pixel_match_color(x, y, expected_RGB_color, tolerance=0):
    """
    Verifica se a cor de um pixel na tela corresponde a um valor esperado.
    
    Args:
        x (int): Coordenada x do pixel.
        y (int): Coordenada y do pixel.
        expected_RGB_color (tuple): Cor esperada no formato (R, G, B).
        tolerance (int, opcional): Tolerância na comparação de cores. Padrão é 0.
    
    Returns:
        bool: True se a cor corresponder dentro da tolerância, False caso contrário.
    """
    pix = screenshot(region=(x, y, 1, 1))[0, 0, ::-1]
    expected = np.array(expected_RGB_color)
    return (np.abs(pix - expected) < tolerance).all()
