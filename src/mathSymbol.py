##    DPRL CROHME 2013
##    Copyright (c) 2013-2014 Lei Hu, Kenny Davila, Francisco Alvaro, Richard Zanibbi
##
##    This file is part of DPRL CROHME 2013.
##
##    DPRL CROHME 2013 is free software: 
##    you can redistribute it and/or modify it under the terms of the GNU 
##    General Public License as published by the Free Software Foundation, 
##    either version 3 of the License, or (at your option) any later version.
##
##    DPRL CROHME 2013 is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with DPRL CROHME 2013.  
##    If not, see <http://www.gnu.org/licenses/>.
##
##    Contact:
##        - Lei Hu: lei.hu@rit.edu
##        - Kenny Davila: kxd7282@rit.edu
##        - Francisco Alvaro: falvaro@dsic.upv.es
##        - Richard Zanibbi: rlaz@cs.rit.edu 

import math
from convex import *
from traceInfo import *

#This class represents a math symbol. A math symbol is 
#composed of traces, and features can be extracted to describe it.
#The symbol is labeled by the truth value that comes from a file
#or it can be set to unknown, and later be labeled by a classifier 

class MathSymbol:
    #Define the set of features to use...
    #1, base 8-11,
    useTracesNumber = True
    useLineFeatures = True
    useAspectRatio = True
    useEigenFeatures = True    
    #2
    useCrossings = True
    useAngularCrossings = True
    #3
    use2DHistogram = False
    #4
    useGabor = False
    #5
    usePointAngDist = False
    #6
    useConvexArea = False
    #7
    useSubsegments = True

    #8 base 13
    useSizeRatio = False #cannot be used with SEGMENTER!   
    
    #other weaker features....
    #9 
    useDistancesGrid = False #False (INCLUDE ON ULTRA)
    
    useCDF = False #False (NOT EVEN ON ULTRA)
    
    #...and their number...
    number_crossings = 5
    number_angular = 4
    number_subcrossings = 9 #9
    angular_subcrossings = 1 #1
    size_grid = 4
    n_bins = 8 #16
    size_2d_hist = 4 #4
    gabor_grid = [1, 2, 3] #[3]->c
    angular_bins = 4
    angular_dist = 0.25    
    
    def __init__(self, traces, truth):
        self.traces = traces
        self.truth = truth        

        #process limits...
        self.minX, self.maxX, self.minY, self.maxY = traces[0].getBoundaries()
        for i in range(1, len(traces)):
            newMinX, newMaxX, newMinY, newMaxY = traces[i].getBoundaries()

            if newMinX < self.minX:
                self.minX = newMinX
            if newMaxX >self.maxX:
                self.maxX = newMaxX
            if newMinY < self.minY:
                self.minY = newMinY
            if newMaxY > self.maxY:
                self.maxY = newMaxY

        self.original_box = (self.minX, self.maxX, self.minY, self.maxY)
        self.w_ratio = 1.0
        self.h_ratio = 1.0

    def setSizeRatio(self, avg_width, avg_height):
        if avg_width > 0.0:
            self.w_ratio = (self.original_box[1] - self.original_box[0]) / avg_width
        else:
            self.w_ratio = 1.0

        if avg_height > 0.0:
            self.h_ratio = (self.original_box[3] - self.original_box[2]) / avg_height
        else:
            self.h_ratio = 1.0

    def getSizeRatio(self):
        return (self.w_ratio, self.h_ratio)

    def normalize(self):
        #first, get the bounding box of the whole symbol...
        
        #start with first trace...
        minX, maxX, minY, maxY = self.traces[0].getBoundaries()
        
        #expand if other traces need it
        for i in range(1, len(self.traces)):
            oMinX, oMaxX, oMinY, oMaxY = self.traces[i].getBoundaries()
            
            #min X
            if oMinX < minX:
                minX = oMinX
            #max X
            if oMaxX > maxX:
                maxX = oMaxX
            #min Y
            if oMinY < minY:
                minY = oMinY
            #max Y
            if oMaxY > maxY:
                maxY = oMaxY
                        
        #the original proportions must be keep, check longest side...
        width = maxX - minX
        height = maxY - minY
        if width > height:
            #keep minX, maxX, move Y bounds to keep proportions inside a square
            minY = ((maxY + minY) / 2.0) - (width / 2.0)
            maxY = minY + width
        else:
            #keep minY, maxY, move X bounds to keep proportions inside a square
            minX = ((maxX + minX) / 2.0) - (height / 2.0)
            maxX = minX + height                
        
        current_box = [minX, maxX, minY, maxY]
        
        #relocate and re-scale each trace, to be in the new box [-1, 1],[-1,1]
        new_box = [-1, 1, -1, 1]
        
        for trace in self.traces:
            trace.relocatePoints(current_box, new_box)        
    
    #produce the features vector
    def getFeatures(self):
        features = []
        
        #1) first, crossings...
        if MathSymbol.useCrossings:         
            #...count how many line segments are crossed by horizontal and vertical lines
            #   at different heights and widths
            step = 2.0 / (MathSymbol.number_crossings + 1)
            substep = step / (MathSymbol.number_subcrossings + 1)
            horizontal_count_crossings = []
            horizontal_avg_crossings = []
            horizontal_min_crossings = []
            horizontal_max_crossings = []

            horizontal_area_crossings = []
            horizontal_dist_crossings = []
            
            vertical_count_crossings = []        
            vertical_avg_crossings = []
            vertical_min_crossings = []
            vertical_max_crossings = []

            vertical_area_crossings = []
            vertical_dist_crossings = []
            
            for i in range(1, MathSymbol.number_crossings + 1):
                #horizontal crossings                            
                h_crossings = [0, 0.0, 1.1, -1.1]
                
                init = -1 + i * step

                total_crossings = 0
                avg_x = 0.0
                avg_min = 0.0
                avg_max = 0.0
                area_limits = []
                cross_positions = ['0'] * 3
                for k in range(1, MathSymbol.number_subcrossings + 1):
                    init = -1 + (i - 0.5) * step + k * substep
                    line = [ (-1.1, init), (1.1, init) ]

                    current_min = 1.1
                    current_max = -1.1
                        
                    for t in self.traces:
                        current_crossings = t.getLineCrossings(line)
    
                        for x, y in current_crossings:
                            avg_x += x
                            current_min = min(current_min, x)
                            current_max = max(current_max, x)

                            #discretize x...[-1,-0.5,0,0.5,1]
                            #disc_x = int(round((x + 1.0) * 2.0))
                            #discretize x...[-1,0,1]
                            disc_x = int(round(x + 1.0))
                            cross_positions[ disc_x ] = '1'
                            
                        total_crossings += float(len(current_crossings))

                    #store limits 
                    avg_min += current_min 
                    avg_max += current_max

                    area_limits.append( (current_min, current_max) )

                h_crossings[0] = round((total_crossings * 2.0) / MathSymbol.number_subcrossings) / 2.0

                if total_crossings > 0:
                    h_crossings[1] = avg_x / total_crossings
                    h_crossings[2] = avg_min / float(MathSymbol.number_subcrossings)
                    h_crossings[3] = avg_max / float(MathSymbol.number_subcrossings)
                     
                horizontal_count_crossings.append( h_crossings[0] )  #Count Crossings 
                
                #discretizing... [-1.0, -0.5, 0.0, 0.5, 1.0]
                if total_crossings > 0:
                    avg = ((round((h_crossings[1] + 1.0) * 2.0)) / 2.0) - 1.0
                    current_min = ((round((h_crossings[2] + 1.0) * 2.0)) / 2.0) - 1.0
                    current_max = ((round((h_crossings[3] + 1.0) * 2.0)) / 2.0) - 1.0
                else:
                    avg = -2.0
                    current_min = -2.0
                    current_max = -2.0
                

                #horizontal_avg_crossings.append( str(avg) )             #Average         (Discrete)
                horizontal_avg_crossings.append( h_crossings[1] )       #Average         (Continuous)                
                #horizontal_min_crossings.append( str(current_min) )       #Min             (Continuous)
                horizontal_min_crossings.append( h_crossings[2] )       #Min             (Continuous)
                #horizontal_max_crossings.append( str(current_max) )       #Max             (Continuous)
                horizontal_max_crossings.append( h_crossings[3] )       #Max             (Continuous)

                #The stimation of area inside min and max ...
                total_area = 0.0
                if len(area_limits) > 0:
                    for k in range(len(area_limits) - 1):
                        init_x1, end_x1 = area_limits[k]
                        init_x2, end_x2 = area_limits[k + 1]

                        if init_x1 <= end_x2 and init_x2 <= end_x1 and init_x1 <= end_x1 and init_x2 <= end_x2:
                            #common range...
                            #extract three segments, common and two non-commons
                            w_common = min(end_x1, end_x2) - max(init_x1, init_x2)
                            w_left = max(init_x1, init_x2) - min(init_x1, init_x2)
                            w_right = max(end_x1, end_x2) - min(end_x1, end_x2)

                            total_area += ((w_left + w_right) / 2.0 + w_common) * substep

                horizontal_area_crossings.append( total_area )                        
                horizontal_dist_crossings.append( str(int(''.join(cross_positions), 2)) )
            
                #vertical crossings
                
                v_crossings = [0, 0.0, 1.1, -1.1]

                total_crossings = 0
                avg_y = 0.0
                avg_min = 0.0
                avg_max = 0.0
                area_limits = []
                cross_positions = ['0'] * 3
                for k in range(1, MathSymbol.number_subcrossings + 1):
                    init = -1 + (i - 0.5) * step + k * substep                    
                    line = [ (init, -1.1), (init, 1.1) ]
                    
                    current_min = 1.1
                    current_max = -1.1
                        
                    for t in self.traces:
                        current_crossings = t.getLineCrossings(line)
    
                        for x, y in current_crossings:
                            avg_y += y
                            current_min = min(current_min, y)
                            current_max = max(current_max, y)

                            #discretize y...[-1,-0.5,0,0.5,1]
                            #disc_y = int(round((y + 1.0) * 2.0))
                            #discretize y...[-1,,0,1]
                            disc_y = int(round(y + 1.0))
                            cross_positions[ disc_y ] = '1'
                            
                        total_crossings += float(len(current_crossings))

                    #store limits 
                    avg_min += current_min 
                    avg_max += current_max
                    
                    area_limits.append( (current_min, current_max) )

                v_crossings[0] = round((total_crossings * 2.0) / MathSymbol.number_subcrossings) / 2.0

                if total_crossings > 0:
                    v_crossings[1] = avg_y / total_crossings
                    v_crossings[2] = avg_min / float(MathSymbol.number_subcrossings)
                    v_crossings[3] = avg_max / float(MathSymbol.number_subcrossings)

                vertical_count_crossings.append( v_crossings[0] )  #Count Crossings 

                #discretizing... [-1.0, -0.5, 0.0, 0.5, 1.0]
                if total_crossings > 0:
                    avg = ((round((v_crossings[1] + 1.0) * 2.0)) / 2.0) - 1.0
                    current_min = ((round((v_crossings[2] + 1.0) * 2.0)) / 2.0) - 1.0
                    current_max = ((round((v_crossings[3] + 1.0) * 2.0)) / 2.0) - 1.0
                else:
                    avg = -2.0
                    current_min = -2.0
                    current_max = -2.0

                #vertical_avg_crossings.append( str(avg) )             #Average         (Discrete)
                vertical_avg_crossings.append( v_crossings[1] )       #Average         (Continuous)                
                #vertical_min_crossings.append( str(current_min) )       #Min             (Continuous)
                vertical_min_crossings.append( v_crossings[2] )       #Min             (Continuous)
                #vertical_max_crossings.append( str(current_max) )       #Max             (Continuous)
                vertical_max_crossings.append( v_crossings[3] )       #Max             (Continuous)

                #The stimation of area inside min and max ...
                total_area = 0.0
                if len(area_limits) > 0:
                    for k in range(len(area_limits) - 1):
                        init_y1, end_y1 = area_limits[k]
                        init_y2, end_y2 = area_limits[k + 1]

                        if init_y1 <= end_y2 and init_y2 <= end_y1 and init_y1 <= end_y1 and init_y2 <= end_y2:
                            #common range...
                            #extract three segments, common and two non-commons
                            h_common = min(end_y1, end_y2) - max(init_y1, init_y2)
                            h_top = max(init_y1, init_y2) - min(init_y1, init_y2)
                            h_bottom = max(end_y1, end_y2) - min(end_y1, end_y2)

                            total_area += ((h_top + h_bottom) / 2.0 + h_common) * substep

                vertical_area_crossings.append( total_area )
                vertical_dist_crossings.append( str(int(''.join(cross_positions), 2)) )
            
            features += horizontal_count_crossings          #add discrete values...
            
            #features += horizontal_avg_crossings      #active
            features += horizontal_min_crossings      #active
            features += horizontal_max_crossings      #active
            
            #features += horizontal_dist_crossings
            #features += horizontal_area_crossings
            #features += [ sum( horizontal_area_crossings ) ]
            
            features += vertical_count_crossings            #add discrete values...
            
            #features += vertical_avg_crossings        #active
            features += vertical_min_crossings        #active
            features += vertical_max_crossings        #active

            
            #features += vertical_dist_crossings
            #features += vertical_area_crossings
            #features += [ sum(vertical_area_crossings) ]
        
        
        #1.5) Angular crossings....
        if MathSymbol.useAngularCrossings:
            #get character centroid...
            #try using a threshold for avoiding dense regions affecting
            points = []
            threshold = 0.0 #use squared value of distance
            cx = 0.0
            cy = 0.0
            for t in self.traces:                
                for x1, y1 in t.points:
                    found = False
                    for x2, y2 in points:
                        if (x1 - x2) ** 2 + (y1 - y2) ** 2 <=  threshold:
                            found = True
                            break

                    if not found:
                        points.append( (x1, y1) )
                        cx += x1
                        cy += y1

            if len(points) > 0:
                cx /= len(points)
                cy /= len(points)

            
            step = (math.pi * 0.5) / (MathSymbol.number_angular + 1)
            substep = step / (MathSymbol.angular_subcrossings + 1)
            
            angular_count_crossings = [[],[]]
            angular_avg_crossings = [[],[]]
            angular_min_crossings = [[],[]]
            angular_max_crossings = [[],[]]
            for i in range(1, MathSymbol.number_angular + 1):
                #first r between 0 and 90 degrees (to 180 and 270)
                #second r between 90 and 180 degrees (to 270 and 360)
                for r in range(2):
                    a_crossings = [0, 0.0, 3.0, -3.0]
                    total_crossings = 0
                    avg_dis = 0.0
                    avg_min = 0.0
                    avg_max = 0.0
                    
                    for k in range(1, MathSymbol.angular_subcrossings + 1):
                        #angle = step * i + math.pi * 0.5 * r
                        angle = math.pi * 0.5 * r + (i - 0.5) * step + k * substep
                            
                        init_x = cx + 3 * math.cos(angle)
                        init_y = cy + 3 * math.sin(angle)
                        end_x = cx - 3 * math.cos(angle)
                        end_y = cy - 3 * math.sin(angle)
                        line = [ (init_x, init_y), (end_x, end_y) ]

                        current_min = 3.0
                        current_max = -3.0
                        current_avg = 0.0
                                                
                        for t in self.traces:
                            current_crossings = t.getLineCrossings(line)

                            for x, y in current_crossings:
                                dis = math.sqrt( (x - init_x) ** 2 + (y - init_y) ** 2 ) - 3

                                avg_dis += dis
                                current_min = min( current_min, dis )
                                current_max = max( current_max, dis )
                            
                            total_crossings += float(len(current_crossings))

                        avg_min += current_min
                        avg_max += current_max

                    a_crossings[0] = round(total_crossings / MathSymbol.angular_subcrossings)
                                        
                    if a_crossings[0] > 0:
                        a_crossings[1] /= float(a_crossings[0])

                    if total_crossings > 0:
                        a_crossings[1] = avg_dis / total_crossings
                        a_crossings[2] = avg_min / float(MathSymbol.angular_subcrossings)
                        a_crossings[3] = avg_max / float(MathSymbol.angular_subcrossings)
                        
                    angular_count_crossings[r].append( a_crossings[0] )  #Count Crossings (Discrete)
                    angular_avg_crossings[r].append( a_crossings[1] )       #Average         (Continuous)
                    angular_min_crossings[r].append( a_crossings[2] )       #Min             (Continuous)
                    angular_max_crossings[r].append( a_crossings[3] )       #Max             (Continuous)                
                    
            features += angular_count_crossings[0]            #add discrete values...
            
            #features += angular_avg_crossings[0]        #add continuous values...
            features += angular_min_crossings[0]                    
            features += angular_max_crossings[0]              
            
            features += angular_count_crossings[1]            #add discrete values...
            
            #features += angular_avg_crossings[1]        #add continuous values
            features += angular_min_crossings[1]         
            features += angular_max_crossings[1]
               
        #2) add the number of traces...
        if MathSymbol.useTracesNumber:
            features += [ float(len(self.traces)) ]
                    
        #3) generate a grid of points, get the closest point at each region...
        if MathSymbol.useDistancesGrid:
            step = 2.0 / MathSymbol.size_grid
            distances = []
            for x in range(MathSymbol.size_grid):
                for y in range(MathSymbol.size_grid):
                    px = -1.0 + step * (x + 0.5)
                    py = -1.0 + step * (y + 0.5)                                        
                    
                    min_distance, min_point = self.traces[0].closestDistanceToPoint(px, py)
                    for i in range(1, len(self.traces)):
                        distance, point = self.traces[i].closestDistanceToPoint(px, py)
                        if distance < min_distance:
                            min_distance = distance
                            min_point = point
                    
                    distances.append( min_distance )
                    
            features += distances
            #features.append( distances )                           
        
        #4) of the line itself... (of the type that can be added across traces)
        if MathSymbol.useLineFeatures:
            currentLineFeatures = None        
            for trace in self.traces:
                lineFeatures = trace.lineCumulativeFeatures()            
                
                #check if other traces..
                if currentLineFeatures == None:
                    currentLineFeatures = lineFeatures
                else:
                    
                    for i in range(len(currentLineFeatures)):
                        if lineFeatures[i].__class__.__name__ == "list":
                            #combine them by adding the values inside the list...
                            for j in range(len(lineFeatures[i])):
                                currentLineFeatures[i][j] += lineFeatures[i][j]
                        else:
                            #combine them by adding the values...
                            currentLineFeatures[i] += lineFeatures[i]
            #create the average too
            cumulativeAverages = []
            for i in range(len(currentLineFeatures)):
                if currentLineFeatures[i].__class__.__name__ == "list":
                    avgLineFeatures = []
                    for j in range(len(currentLineFeatures[i])):
                        avgLineFeatures.append( currentLineFeatures[i][j] / len(self.traces) )
                    
                    cumulativeAverages.append( avgLineFeatures )
                else:
                    cumulativeAverages.append( currentLineFeatures[i] / len(self.traces) )
            
                        
            features += currentLineFeatures
            features += cumulativeAverages            
                
        #5) calculate histograms of point distributions
        if MathSymbol.useCDF:            
            vertical_histogram = None
            horizontal_histogram = None
            
            total_points = 0
            for trace in self.traces:
                total_points += len(trace.points)
                current_horizontal, current_vertical = trace.getHistograms(MathSymbol.n_bins)            
                 
                if vertical_histogram == None:
                    horizontal_histogram = current_horizontal 
                    vertical_histogram = current_vertical
                else:
                    for i in range(MathSymbol.n_bins):
                        horizontal_histogram[i] += current_horizontal[i]
                        vertical_histogram[i] += current_vertical[i]                        
                
            #normalize...
            for i in range(MathSymbol.n_bins):
                horizontal_histogram[i] /= float(total_points)  
                vertical_histogram[i] /= float(total_points)
                        
            #generate CDF's
            horizontal_cdf = []
            vertical_cdf = []
            total_horizontal = 0.0
            total_vertical = 0.0
            for i in range(MathSymbol.n_bins - 1):
                #horizontal...
                total_horizontal += horizontal_histogram[i]
                horizontal_cdf.append( total_horizontal )
                #vertical
                total_vertical += vertical_histogram[i]
                vertical_cdf.append( total_vertical )
                
            #threat as vectors...
            features.append( horizontal_cdf )
            features.append( vertical_cdf )            
            
        #6) 2D histogram
        if MathSymbol.use2DHistogram:
            bidimensional_hist = None
            total_points = 0.0
            for trace in self.traces:
                total_points += float(len(trace.points))
                current_histogram = trace.get2DHistogram(MathSymbol.size_2d_hist)
                
                if bidimensional_hist == None:
                    #just assign...
                    bidimensional_hist = current_histogram
                else:
                    #combine...
                    for y in range(MathSymbol.size_2d_hist):
                        for x in range(MathSymbol.size_2d_hist):
                            bidimensional_hist[y][x] += current_histogram[y][x]
            
            #then, normalize!
            for y in range(MathSymbol.size_2d_hist):
                for x in range(MathSymbol.size_2d_hist):
                    bidimensional_hist[y][x] /= total_points
            
            #add to feature vector (as list of continuous attributes)
            for hist in bidimensional_hist:
                features += hist

        #7) Gabor filters...
        if MathSymbol.useGabor:
            for size in MathSymbol.gabor_grid:
                symbol_gabor = [ 0.0, 0.0, 0.0, 0.0] * size * size
                gabors = []
                lengths = []
                total_length = 0.0
                
                for trace in self.traces:                
                    trace_gabor, trace_length = trace.getGabor(size)
                    
                    gabors.append( trace_gabor )
                    lengths.append( trace_length )

                    total_length += trace_length

                if total_length > 0.0:                    
                    for t in range(len(self.traces)):
                        w = lengths[t] / total_length
                    
                        for i in range(len(symbol_gabor)):
                            symbol_gabor[i] += gabors[t][i] * w

                features += symbol_gabor

        #8) Aspect Ratio...
        if MathSymbol.useAspectRatio:
            min_x = 1
            max_x = -1
            min_y = 1
            max_y = -1
            for trace in self.traces:
                t_minX, t_maxX, t_minY, t_maxY = trace.getBoundaries()
                min_x = min(t_minX, min_x)
                max_x = max(t_maxX, max_x)
                min_y = min(t_minY, min_y)
                max_y = max(t_maxY, max_y)

            w = (max_x - min_x)
            h = (max_y - min_y)
            if w <= 0.01:
                w = 0.01
            if h <= 0.01:
                h = 0.1
                
            features.append( [ (w / h) ] ) #add as a 1-D vector        

        #9) points Angular Dist
        if MathSymbol.usePointAngDist:
            points = []
            sharp_points = []
            #put together all sharp points..
            for trace in self.traces:
                points += trace.points
                sharp_points += trace.sharp_points

            #get the sharp_points average....
            avg_x = 0.0
            avg_y = 0.0
            for p in sharp_points:
                x = p[1][0]
                y = p[1][1]

                avg_x += x
                avg_y += y

            avg_x /= len(sharp_points)
            avg_y /= len(sharp_points)

            #calculate angular distribution...
            #....relative to sharp points average...
            distribution = [ 0.0] + ([0.0] * MathSymbol.angular_bins)
            point_w = 1.0 / len(points)

            for p in points:
                x = p[0] - avg_x
                y = p[1] - avg_y
                
                dist = math.sqrt( x ** 2 + y ** 2 )
                w0 = 1.0 - (min(dist, MathSymbol.angular_dist) / MathSymbol.angular_dist)

                divisor = (math.pi * 2) / MathSymbol.angular_bins 

                ang_r = (math.atan2( y, x ) + math.pi) / divisor
                
                r0 = int(ang_r) % MathSymbol.angular_bins                 
                r1 = (r0 + 1) % MathSymbol.angular_bins
                
                wr0 = ang_r - int(ang_r)
                
                distribution[0] += w0 * point_w
                distribution[1 + r0] += (1.0 - w0) * wr0 * point_w
                distribution[1 + r1] += (1.0 - w0) * (1 - wr0) * point_w

            features += distribution
            features += [ avg_x, avg_y ]

        #10) features based on convex hulls of the strokes
        if MathSymbol.useConvexArea:
            points = []
            
            min_area = -1
            max_area = -1
            avg_area = 0

            min_perimeter = -1
            max_perimeter = -1
            avg_perimeter = 0
            
            for i in range(len(self.traces)):
                points += self.traces[i].points                

                if len(self.traces[i].points) > 1:
                    hull = convexHull(self.traces[i].points)                    
                    hull_area = convexArea(hull)
                    hull_perim = convexPerimeter(hull)
                else:
                    hull_area = 0
                    hull_perim = 0.0

                avg_area += hull_area
                if min_area == -1 or min_area > hull_area:
                    min_area = hull_area
                if max_area == -1 or max_area < hull_area:
                    max_area = hull_area

                avg_perimeter += hull_perim
                if min_perimeter == -1 or min_perimeter > hull_perim:
                    min_perimeter = hull_perim
                if max_perimeter == -1 or max_perimeter < hull_perim:
                    max_perimeter = hull_perim                

            avg_area /= len(self.traces)
            avg_perimeter /= len(self.traces)            

            #now, remove duplicated points...
            self.removeDuplicatedPoints(points)
            if len(points) > 2:
                hull = convexHull(points)
                hull_area = convexArea(hull)
                hull_perim = convexPerimeter(hull)
            else:
                hull_area = 0.0
                hull_perim = 0.0

            left_hull = []
            right_hull = []
            top_hull = []
            bottom_hull = []
            for x,y in points:
                if x <= 0.0:
                    left_hull.append( (x, y) )
                else:
                    right_hull.append( (x, y) )
                    
                if y <= 0.0:
                    top_hull.append( (x,y) )
                else:
                    bottom_hull.append( (x, y))

            #left convex hull area
            if len(left_hull) > 2:
                left_convex = convexHull( left_hull )
                left_area = convexArea( left_convex )
                left_perimeter = convexPerimeter( left_convex )
            else:
                left_area = 0.0
                left_perimeter = 0.0

            #right convex hull area
            if len(right_hull) > 2:
                right_convex = convexHull( right_hull )
                right_area = convexArea( right_convex )
                right_perimeter = convexPerimeter( right_convex )
            else:
                right_area = 0.0
                right_perimeter = 0.0

            #top convex hull area
            if len(top_hull) > 2:
                top_convex = convexHull( top_hull )
                top_area = convexArea( top_convex )
                top_perimeter = convexPerimeter( top_convex )
            else:
                top_area = 0.0
                top_perimeter = 0.0

            #bottom convex hull area
            if len(bottom_hull) > 2:
                bottom_convex = convexHull( bottom_hull )
                bottom_area = convexArea( bottom_convex )
                bottom_perimeter = convexPerimeter( bottom_convex )
            else:
                bottom_area = 0.0
                bottom_perimeter = 0.0                    
            
            features += [ hull_area, left_area, right_area, top_area, bottom_area ]
            features += [ avg_area, min_area, max_area ]
            
            features += [ hull_perim, left_perimeter, right_perimeter, top_perimeter, bottom_perimeter]
            features += [ avg_perimeter, min_perimeter, max_perimeter ]

        #11) Subsegments:
        if MathSymbol.useSubsegments:

            total_str = 0.0
            total_curv = 0.0            
            total_dist_str = [[ 0.0 for x in range(4) ] for y in range(4)]
            total_dist_crv = [ 0.0 ] * 4
            total_dist_arc = [ 0.0 ] * 4
            for t in self.traces:
                #length of straight lines
                #length of curves
                l_str, l_curv, dist_str, dist_crv, dist_arc = t.getTypeSubsegmentsInfo()                

                total_str += l_str
                total_curv += l_curv

                for i in range(len(total_dist_str)):
                    for k in range(len(total_dist_str[i])):
                        total_dist_str[i][k] += dist_str[i][k]

                for i in range(len(total_dist_crv)):
                    total_dist_crv[i] += dist_crv[i]

                for i in range(len(total_dist_arc)):
                    total_dist_arc[i] += dist_arc[i]
            
            total_length = total_str + total_curv
            if total_length > 0.0:
                percent_str = ( total_str ) / ( total_length )
            else:
                #50%??? .... not straight, neither all curved...
                percent_str = 0.5

            #normalize distributions...
            if total_str > 0.0:
                for i in range(len(total_dist_str)):
                    for k in range(len(total_dist_str[i])):
                        total_dist_str[i][k] /= total_length
                    
            if total_curv > 0.0:
                for i in range(len(total_dist_crv)):
                    total_dist_crv[i] /= total_length
                    
                for i in range(len(total_dist_arc)):
                    total_dist_arc[i] /= total_length

            #features += [ [percent_str], [total_str], [total_curv]]
            #features += [ [percent_str] ]
            
            for z in range(len(total_dist_str)):
                if z == 0 or z == 1:
                    x = total_dist_str[z]
                    features += x
                
            #features += [[x] for x in total_dist_crv ]
            #features += [[x] for x in total_dist_arc ]
            
            """
            if self.truth == '5':
                self.saveAsSVG('TEMPORAL.svg')
                x = 5 / 0
            
            """

        #12) "Eigen" Features (based on covariance)
        if MathSymbol.useEigenFeatures:
            
            #add covariance matrix of all points....
            total_points = 0
            mean_x = 0
            mean_y = 0
            for i in range(len(self.traces)):
                points = self.traces[i].points

                for x, y in points:
                    mean_x += x
                    mean_y += y

                total_points += len(points)

            mean_x /= total_points
            mean_y /= total_points

            var_x = 0
            var_y = 0
            cov_xy = 0
            for i in range(len(self.traces)):
                points = self.traces[i].points

                for x, y in points:
                    var_x += (x - mean_x) ** 2
                    var_y += (y - mean_y) ** 2
                    cov_xy += (x - mean_x) * (y - mean_y)

            var_x /= total_points
            var_y /= total_points
            cov_xy /= total_points

            features += [ var_x, var_y, cov_xy ]

        #13) Size ratio relative to AVG of other symbols...
        if MathSymbol.useSizeRatio:
            features += [ self.w_ratio, self.h_ratio ]
            
            
        
        return features
    
    def getFeaturesTypes(self):
        types = []
                           
        #1) Crossings        
        if MathSymbol.useCrossings:
            #use as list of discrete values
            #cross_types = ['d'] * MathSymbol.number_crossings
            cross_types = ['c'] * MathSymbol.number_crossings
            
            #use as a list of continuous attributes...
            #cross_types += ([ 'c' ] * MathSymbol.number_crossings * 3)

            cross_types += ([ 'c' ] * MathSymbol.number_crossings * 2)
            #cross_types += ([ 'd' ] * MathSymbol.number_crossings * 2 + ['v1'] * MathSymbol.number_crossings * 1)
                                             
            types += cross_types * 2 #horizontal + vertical
        
        #1.5) Angular Crossings...
        if MathSymbol.useAngularCrossings:
            #use as list of discrete values
            #cross_types = ['d'] * MathSymbol.number_angular
            cross_types = ['c'] * MathSymbol.number_angular
            
            #use as list of continuous attributes...
            #cross_types += ([ 'c' ] * MathSymbol.number_angular * 3)
            cross_types += ([ 'c' ] * MathSymbol.number_angular * 2)
                        
            types += cross_types * 2    #region 1 + region 2
            
        
        #2) # Traces (Discrete)
        if MathSymbol.useTracesNumber:
            types += [ 'c' ]
        
        #3) Distances of points (Continuous)
        if MathSymbol.useDistancesGrid:
            #using as a list of continuous attributes        
            types += [ 'c' for x in range(MathSymbol.size_grid * MathSymbol.size_grid) ]
            
            #un-comment when using as a vector       
            #types += [ ('v' + str((MathSymbol.size_grid * MathSymbol.size_grid))) ]
        
        #4) of the lines...plus averages...
        if MathSymbol.useLineFeatures:
            #some of these might be used as vectors...
            types += (self.traces[0].lineCumulativeFeaturesTypes() * 2)            
        
        #5) types of the CDF's (continuous)
        if MathSymbol.useCDF:        
            #Un-comment when used as list of continuous attributes
            #types += [ 'c' for x in range((MathSymbol.n_bins - 1) * 2)]
            
            #Un-comment when used as vector for histograms
            #types += ([ 'v' + str(MathSymbol.n_bins) ] * 2)
            
            #used as vector of cumulative distribution function
            #types += ([ 'v' + str(MathSymbol.n_bins - 1) ] * 2)

            types += ([ 'v1' ] * (MathSymbol.n_bins - 1) * 2)
            
        
        #6) 2D histogram 
        if MathSymbol.use2DHistogram:
            types += ([ 'c' ] * MathSymbol.size_2d_hist * MathSymbol.size_2d_hist )

        #7) Gabor
        if MathSymbol.useGabor:
            for size in MathSymbol.gabor_grid:
                types += [ 'c', 'c', 'c', 'c' ] * size * size
                #types += [ 'v4' ] * size * size

        #8) Aspect Ratio
        if MathSymbol.useAspectRatio:
            types += ['c']
            

        #9) Sharp points Angular Dist
        if MathSymbol.usePointAngDist:
            types += (['c'] + (['c'] * MathSymbol.angular_bins))
            types += ['c','c']

        #10) Convex Hull Area:
        if MathSymbol.useConvexArea:
            #types += [ 'v1' ] * 16
            types += [ 'c' ] * 16

        #11) Subsegments:
        if MathSymbol.useSubsegments:
            types += self.traces[0].getSubsegmentsFeaturesTypes()

        #12) Eigen features:
        if MathSymbol.useEigenFeatures:
            types += [ 'c' ] * 3

        #13) Size ratio relative to AVG of other symbols...
        if MathSymbol.useSizeRatio:
            types += [ 'c', 'c' ]
            
        
        return types

    def filterCrossings(self, crossings):
        #check for "repeated" crossings ...
        #parts were it should be considered as one single crossing
        threshold = 0.0
        i = 0
        while i < len(crossings):
            j = i + 1
            while j < len(crossings):
                dif_x = crossings[i][0] - crossings[j][0]
                dif_y = crossings[i][1] - crossings[j][1]
                
                if math.sqrt( (dif_x ** 2) + (dif_y ** 2) ) <= threshold:
                    del crossings[j]
                else:
                    j += 1

            i += 1

    def saveAsSVG(self, path):
        f = open(path, 'w')

        f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\r\n')
        f.write('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN"')
        f.write(' "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">\r\n')
        f.write('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"')
        f.write('   fill-rule="evenodd" height="10.0in" preserveAspectRatio="none" stroke-linecap="round"')
        f.write('   viewBox="-1.1 -1.1 2.2 2.2" width="10.0in">\r\n')

        f.write('<style type="text/css">\r\n')
        f.write('.pen0 { stroke: rgb(0,0,0); stroke-width: 0.005; stroke-linejoin: round; }\r\n')
        f.write('.pen1 { stroke: rgb(255,0,0); stroke-width: 0.005; stroke-linejoin: round; }\r\n')
        f.write('.pen2 { stroke: rgb(0,255,0); stroke-width: 0.005; stroke-linejoin: round; }\r\n')
        f.write('</style>\r\n')

        f.write('<g>\r\n')

        #The strokes...
        for t in self.traces:

            polyline = ''
            for p in t.points:
                x, y = p
                polyline += str(x) + "," + str(y) + ' '
                f.write('<circle cx="' + str(x) + '" cy="' + str(y) + '" r="0.01" fill="blue"/>\n')

            if t.segments == None:
                #write the entire polyline...
                f.write('<polyline class="pen0" fill="none" points="' + polyline + '"/>\n')
            else:
                #write the segments...
                for init, end, ang, stype, l in t.segments:
                    pen = 'pen1' if stype == 1 else 'pen2'

                    line = ''
                    for p in range(init, end + 1):
                        x, y = t.points[p]
                        line += str(x) + "," + str(y) + ' '
                    f.write('<polyline class="' + pen + '" fill="none" points="' + line + '"/>\n')

            

        f.write('</g>\r\n')
        f.write('</svg>\r\n')    
    
        f.close()

    def removeDuplicatedPoints(self,points):
        i = 0
        while i < len(points):
            j = i + 1
            while j < len(points):
                if points[i] == points[j]:
                    del points[j]
                else:
                    j += 1
                    
            i += 1
