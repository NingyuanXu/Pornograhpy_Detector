Project plans:
1. Check every pixel, detect the color and whether it is skin
2. Classify the areas, get multiple areas
3. Remove areas with few pixels, turn into black-and-white image

Criteria for NON-porn:
1. Skin areas < 3
2. Skin area / total image area < 15%
3. Maximum skin area < 45% * Total skin area
4. Skin area > 60

This criteria is subject to change. Though it works well for given image, it does not work for every image. That is why this project still needs to be improved

Note:
1. For each pixel, instead of checking all eight pixels nearby, we only check four pixels, left, up, upper-left and upper-right. This is because during the iteration we are only able to reach this four pixels before reaching out other pixels.
2. There are three ways to classify skin, RGB, HSV, and YCbCr. In this example we only choose ycbcr classifier, but we can choose others.
3. Exact formula for RGB, HSV,ycbcr are collected online. http://blog.csdn.net/hanshanbuleng/article/details/80383813