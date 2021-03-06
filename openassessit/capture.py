from selenium import webdriver
from PIL import Image
from io import BytesIO
import time
import re
import argparse
import os
import json
from utils import generate_img_filename
from templates import template_path


def get_args():
    example_text = '''
    examples:

    python openassessit/%(capture_element_pic)s --input-file="/abs/path/to/lighthouse-report.json" --assets-dir="/abs/path/to/assets" --sleep=1 --driver=firefox

    ''' % {'capture_element_pic': os.path.basename(__file__)}

    parser = argparse.ArgumentParser(epilog=example_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input-file', help='Use absolute path to the lighthouse json report')
    parser.add_argument('-a', '--assets-dir', help='Use absolute path to /assets dir')
    parser.add_argument('-s', '--sleep', type=float, help='Number of seconds to wait before taking screenshots')
    parser.add_argument('-d', '--driver', choices=['firefox', 'chrome'], help='Name of the webdriver.')
    return parser.parse_args()


def get_firefox_driver():
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    return webdriver.Firefox(firefox_options=options)


def get_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    return webdriver.Chrome(chrome_options=options)


def capture_screenshot(assets_dir, url, sleep, driver):
    driver.get(url)
    time.sleep(sleep)
    driver.set_window_size(1400, 700)
    Image.open(BytesIO(driver.get_screenshot_as_png())).save(os.path.join(assets_dir,'screenshot.png'))
    print(os.path.join(assets_dir,'screenshot.png'))


def capture_element_pic(input_file, assets_dir, url, elem_identifier, sleep, driver):

    driver.get(url)
    time.sleep(sleep) # wait for page to load a bit
    driver.set_window_size(1400, driver.execute_script("return document.body.parentNode.scrollHeight"))

    try:
        elem = driver.find_element_by_css_selector(elem_identifier) # find element
        location = elem.location
        size = elem.size

        im = Image.open(BytesIO(driver.get_screenshot_as_png())) # uses PIL library to open image in memory
        im = im.crop((location['x'] -25,
                    location['y'],
                    location['x'] + size['width'] + 25,
                    location['y'] + size['height']
                    ))
        elem_image_name = generate_img_filename(url, elem_identifier)
        im.save(os.path.join(assets_dir,elem_image_name)) # saves new cropped image
        print(os.path.join(assets_dir,elem_image_name))
    except Exception as ex:
        print(ex)


def identifier_generator(data, *auditref_whitelist):

    for sel in auditref_whitelist:
        audit = data.get('audits', {}).get(sel)

        if audit is None:
            print("Invalid audit id: %s" % sel)
            continue

        for item in audit.get('details', {}).get('items', []):
            if item['node']['selector'] == ':root':
                print('Selector returned as ":root", no image will be created.') # If Axe returns ":root" it does not create a helpful screenshot
            else:
                yield item['node']['selector']


def main():
    args = get_args()
    input_file = args.input_file
    assets_dir = args.assets_dir
    sleep = args.sleep
    if args.driver == 'firefox':
        driver = get_firefox_driver()
    elif args.driver == 'chrome':
        driver = get_chrome_driver()
    else:
        raise ValueError("Driver must be one of: firefox, chrome")
    try:
        with open(input_file) as json_file:
            data = json.load(json_file)
            capture_screenshot(assets_dir, data['finalUrl'], sleep, driver)
        for sel in identifier_generator(data, 'color-contrast', 'link-name', 'button-name', 'image-alt', 'input-image-alt', 'label', 'accesskeys', 'frame-title'):
            capture_element_pic(input_file, assets_dir, data['finalUrl'], sel, sleep, driver)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
