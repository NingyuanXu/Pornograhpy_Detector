import sys
import os
import _io
from collections import namedtuple
from PIL import Image

class Nude(object):

    Skin = namedtuple("Skin","id skin region x y")

    def __init__(self, path_or_image):
    # if path_or_image is an instance of Image.Image, assign directly
        if isinstance(path_or_image, Image.Image):
            self.image = path_or_image
    # if path_or_image is str, open the image
        elif isinstance(path_or_image, str):
            self.image = Image.open(path_or_image)
        # get the color tunnel of the image
        bands = self.image.getbands()
        # if it is a single tunnel (grey image), convert into RGB
        if len(bands) == 1:
            # create RGB of same size
            new_img = Image.new("RGB", self.image.size)
            # copy the grey image self.image into new RGB
            new_img.paste(self.image)
            f = self.image.filename
            # substitute the old self.image
            self.image = new_img
            self.image.filename = f
        # store all images corresponding to skin object
        self.skin_map = []
        # detected_regions are detected areas, elements are skin objects.
        self.detected_regions = []
        # elements all areas waited to be merged in int type
        self.merge_regions = []
        # skin regions, index is region, elements are skin objects
        self.skin_regions = []
        # skin regions last merged, initialize as -1
        self.last_from, self.last_to = -1, -1
        # result of porn detector
        self.result = None
        # messages processed
        self.message = None
        # height and width of the image
        self.width, self.height = self.image.size
        # total pixel of images
        self.total_pixels = self.width * self.height

    def resize(self, maxwidth=1000, maxheight=1000):
        """
        resize the image based on maxwidth and maxheight
        if no change, return 0
        if width > maxwidth, return 1
        if height > maxheight, return 2
        if both, return 3

        """

        # return value
        ret = 0
        if maxwidth:
            if self.width > maxwidth:
                wpercent = (maxwidth / self.width)
                hsize = int((self.height * wpercent))
                fname = self.image.filename
                # Image.LANCZOS prevents ensure image qualities
                self.image = self.image.resize((maxwidth, hsize), Image.LANCZOS)
                self.image.filename = fname
                self.width, self.height = self.image.size
                self.total_pixels = self.width * self.height
                ret += 1
        if maxheight:
            if self.height > maxheight:
                hpercent = (maxheight / float(self.height))
                wsize = int((float(self.width) * float(hpercent)))
                fname = self.image.filename
                self.image = self.image.resize((wsize, maxheight), Image.LANCZOS)
                self.image.filename = fname
                self.width, self.height = self.image.size
                self.total_pixels = self.width * self.height
                ret += 2
        return ret


    def parse(self):
        # if already have results, return objects
        if self.result is not None:
            return self
        # get all pixels from image
        pixels = self.image.load()
        # iterate through all pixels
        for y in range(self.height):
            for x in range(self.width):
                # get RGB three components values
                r = pixels[x, y][0]
                g = pixels[x, y][1]
                b = pixels[x, y][2]
                # detect whether this pixel is skin
                isSkin = True if self._classify_skin(r, g, b) else False
                # give each pixel a id, starting from 1 instead of 0
                _id = x + y * self.width + 1
                # create skin object for every pixel, add into self.skin_map
                self.skin_map.append(self.Skin(_id, isSkin, None, x, y))
                # if current pixel is not skin, break out of loop
                if not isSkin:
                    continue

                # check four pixels in total, left, up, upper_left, upper_right
                check_indexes = [_id - 2,
                                 _id - self.width - 2,
                                 _id - self.width - 1,
                                 _id - self.width]
                # record region number of near skin pixel, initialize to -1
                region = -1
                # iterate every neighbourhood pixel
                for index in check_indexes:
                    try:
                        self.skin_map[index]
                    except IndexError:
                        break
                    # if near pixel is a skin pixel
                    if self.skin_map[index].skin:
                        # if current pixel and near pixel are valid, and they are different,
                        # and not added to merge_regions
                        if (self.skin_map[index].region != None and region != None
                        and region != -1 and self.skin_map[index].region != region and
                        self.last_from != region and
                        self.last_to != self.skin_map[index].region):
                            # merge these two regions
                            self._add_merge(region, self.skin_map[index].region)
                        # record this region area
                        region = self.skin_map[index].region
                # all near regions are not skin pixels
                if region == -1:
                    # nametuple can only be changed by replace
                    _skin = self.skin_map[_id - 1]._replace(region=len(self.detected_regions))
                    self.skin_map[_id - 1] = _skin
                    self.detected_regions.append([self.skin_map[_id - 1]])
                # this region number is valid skin pixel
                elif region != None:
                    # change the region number to be same as that of near pixel
                    _skin = self.skin_map[_id - 1]._replace(region=region)
                    self.skin_map[_id - 1] = _skin
                    # add this pixel to detect_regions
                    self.detected_regions[region].append(self.skin_map[_id - 1])
        # all merged areas will be stored into self.skin_regions
        self._merge(self.detected_regions, self.merge_regions)
        # analyze regions and get results
        self._analyse_regions()
        return self


    # self.merge_regions all int type
    # every element contains two int representing two regions to be merged
    # this function adds two region numbers to be merged into self.merge_regions
    def _add_merge(self, _from, _to):
        self.last_from = _from
        self.last_to = _to
        # record self.merge_regions initialize to -1
        from_index = -1
        to_index = -1
        # iterate every element in self.merge_regions
        for index, region in enumerate(self.merge_regions):
            # iterate every region number
            for r_index in region:
                if r_index == _from:
                    from_index = index
                if r_index == _to:
                    to_index = index
        # if two regions are in self.merge
        if from_index != -1 and to_index != -1:
            # if two regions both in merge_region, merge two regions
            if from_index != to_index:
                self.merge_regions[from_index].extend(self.merge_regions[to_index])
                del (self.merge_regions[to_index])
            return
        # if two regions are both not in self.merge_regions
        if from_index == -1 and to_index == -1:
            # create new element in merge_regions
            self.merge_regions.append([_from, _to])
            return
        # if one region is in merge_region and the other is not
        if from_index != -1 and to_index == -1:
            # append non-exist one to exist one
            self.merge_regions[from_index].append(_to)
            return
        # if one region is in merge_region and the other is not
        if from_index == -1 and to_index != -1:
            # append non-exist one to exist one
            self.merge_regions[to_index].append(_from)
            return



    def _merge(self, detected_regions, merge_regions):
        # create new list new_detected regions
        # elements contain skin objects
        new_detected_regions = []
        # merge all elements in merge_regions
        for index, region in enumerate(merge_regions):
            try:
                new_detected_regions[index]
            except IndexError:
                new_detected_regions.append([])
            for r_index in region:
                new_detected_regions[index].extend(detected_regions[r_index])
                detected_regions[r_index] = []
        # add rest skin areas into new_detect_region
        for region in detected_regions:
            if len(region) > 0:
                new_detected_regions.append(region)
        # clear new_detected_regions
        self._clear_regions(new_detected_regions)


    # only save pixels containing areas with numbers larger than specify
    def _clear_regions(self, detected_regions):
        for region in detected_regions:
            if len(region) > 30:
                self.skin_regions.append(region)


    def _analyse_regions(self):
        # if total number of skin area is smaller than 3, not porn
        if len(self.skin_regions) < 3:
            self.message = "Less than 3 skin regions ({_skin_regions_size})".format(
                _skin_regions_size=len(self.skin_regions))
            self.result = False
            return self.result
        # sort skin region based on number of pixels
        self.skin_regions = sorted(self.skin_regions, key=lambda s: len(s),
                                   reverse=True)
        # calculate the total number of skin pixels
        total_skin = float(sum([len(skin_region) for skin_region in self.skin_regions]))
        # if skin area is less than 15% total area of the image, not porn
        if total_skin / self.total_pixels * 100 < 15:
            self.message = "Total skin percentage lower than 15 ({:.2f})".format(total_skin / self.total_pixels * 100)
            self.result = False
            return self.result
        # if max skin area is less than 45% of total skin area, not porn
        if len(self.skin_regions[0]) / total_skin * 100 < 45:
            self.message = "The biggest region contains less than 45 ({:.2f})".format(len(self.skin_regions[0]) / total_skin * 100)
            self.result = False
            return self.result
        # if total number of skin more than 60, not porn
        if len(self.skin_regions) > 60:
            self.message = "More than 60 skins ({})".format(len(self.skin_regions))
            self.result = False
            return self.result
        # else, porn!
        self.message = "This is a Porn !!"
        self.result = True
        return self.result

    def _classify_skin(self, r, g, b):
        # classify based on RGB
        rgb_classifier = r > 95 and \
                         g > 40 and g < 100 and \
                         b > 20 and \
                         max([r, g, b]) - min([r, g, b]) > 15 and \
                         abs(r - g) > 15 and \
                         r > g and \
                         r > b
        # process RGB
        nr, ng, nb = self._to_normalized(r, g, b)
        norm_rgb_classifier = nr / ng > 1.185 and \
                              float(r * b) / ((r + g + b) ** 2) > 0.107 and \
                              float(r * g) / ((r + g + b) ** 2) > 0.112
        # classify based on HSV color
        h, s, v = self._to_hsv(r, g, b)
        hsv_classfifier = h > 0 and \
                          h < 35 and \
                          s > 0.23 and \
                          s < 0.68
        # classify based on YCbCr
        y, cb, cr = self._to_ycbcr(r, g, b)
        ycbcr_classifier = 97.5 <= cb <= 142.5 and 134 <= cr <= 176

        return ycbcr_classifier

    def _to_normalized(self, r, g, b):
        if r == 0:
            r = 0.0001
        if g == 0:
            g = 0.0001
        if b == 0:
            b = 0.0001
        _sum = float(r + g + b)
        return [r / _sum, g / _sum, b / _sum]

    def _to_ycbcr(self, r, g, b):
        y = .299 * r + .587 * g + .114 * b
        cb = 128 - 0.168736 * r - 0.331364 * g + 0.5 * b
        cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
        return y, cb, cr

    def _to_hsv(self, r, g, b):
        h = 0
        _sum = float(r + g + b)
        _max = float(max([r, g, b]))
        _min = float(min([r, g, b]))
        diff = float(_max - _min)
        if _sum == 0:
            _sum = 0.0001

        if _max == r:
            if diff == 0:
                h = sys.maxsize
            else:
                h = (g - b) / diff
        elif _max == g:
            h = 2 + ((g - r) / diff)
        else:
            h = 4 + ((r - g) / diff)

        h *= 60
        if h < 0:
            h += 360

        return [h, 1.0 - (3.0 * (_min / _sum)), (1.0 / 3.0) * _max]


    def inspect(self):
        _image = '{} {} {}×{}'.format(self.image.filename, self.image.format, self.width, self.height)
        return "{_image}: result={_result} message ='{_message}'".format(_image=_image, _result=self.result,
                                                                         _message=self.message)

    def showSkinRegions(self):
        # if no result, return
        if self.result is None:
            return
        # set of skin pixel
        skinIdSet = set()
        # copy one original image
        simage = self.image
        # load the data using copied version
        simageData = simage.load()
        # store skin id into skinIdSet
        for sr in self.skin_regions:
            for pixel in sr:
                skinIdSet.add(pixel.id)
        # change skin pixel into white, others into black
        for pixel in self.skin_map:
            if pixel.id not in skinIdSet:
                simageData[pixel.x, pixel.y] = 0, 0, 0
            else:
                simageData[pixel.x, pixel.y] = 255, 255, 255
        # absolute path
        filePath = os.path.abspath(self.image.filename)
        # directory of file
        fileDirectory = os.path.dirname(filePath) + '/'
        # full name of directory
        fileFullName = os.path.basename(filePath)
        # get file name and extname
        fileName, fileExtName = os.path.splitext(fileFullName)
        # save the image
        simage.save('{}{}_{}{}'.format(fileDirectory, fileName, 'Nude' if self.result else 'Normal', fileExtName))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Detect nudity in images.')
    parser.add_argument('files', metavar='image', nargs='+', help='Images you wish to test')
    parser.add_argument('-r', '--resize',action='store_true', help='Reduce image size to increase speed of scanning')
    parser.add_argument('-v','--visualization', action='store_true', help='Generating areas of skin image')

    args = parser.parse_args()

    for fname in args.files:
        if os.path.isfile(fname):
            n = Nude(fname)
            if args.resize:
                n.resize(maxheight = 800, maxwidth = 600)
            n.parse()
            if args.visualization:
                n.showSkinRegions()
            print(n.result, n.inspect())
        else:
            print(fname, "is not a file")

