import inkex
import simplepath
import math

HEIDENHAIN_RAPID_FEED = 6000

def heiden_begin( n ):
    return 'BEGIN PGM %d MM' % n

def heiden_end( n ):
    return 'END PGM %d MM' % n

def heiden_zup( z ):
    return "L Z" + "{:+4.3f}".format( z ) + " R F%d M" %HEIDENHAIN_RAPID_FEED

def heiden_zmove( z, f ):
    return "L Z%+4.3f R F%d M" % (z, f)

def heiden_xymove( x, y, f ):
    return "L X%+4.3f Y%+4.3f R F%d M" % (x, y, f)

def heiden_xyzmove( x, y, z, f ):
    return "L X%+4.3f Y%+4.3f Z%+4.3f R F%d M" % (x, y, z, f)

#Return the lowest X value in path
def leftmost( path ):
	lm = 10000
	for element in path:
		if element[1][0] < lm:
			lm = element[1][0]
	return lm

#Return the highest X value in path
def rightmost( path ):
	rm = 0
	for element in path:
		if element[1][0] > rm:
			rm = element[1][0]
	return rm

#Compare paths by x coordinate
def cmpPathsX( a, b ):
	if leftmost( a ) < leftmost( b ):
		return -1
	elif leftmost( a ) > leftmost( b ):
		return 1

	return 0

def pathWidth( p ):
    return rightmost( p ) - leftmost( p )

#Center path over X0
def hcenterX( p ):
    lm = leftmost( p )
    w = (rightmost( p ) - lm) / 2
    for e in p:
        e[1][0] = (e[1][0] - lm - (w / 2))


#Main effect class
class HeidengravePathToNC( inkex.Effect ):
    def __init__( self ):
        inkex.Effect.__init__( self )
        
        #Create parameters
        self.OptionParser.add_option('--zsafe', action = 'store', type = 'float', \
                dest = 'zsafe', default = '0.2', help = 'Z coordinate for moving in XY.' )
        self.OptionParser.add_option('--depth', action = 'store', type = 'float', \
                dest = 'depth', default = '0.3', help = 'Z for working in XY.' )
        self.OptionParser.add_option('--feed', action = 'store', type = 'int', \
                dest = 'feed', default = '30', help = 'Feed for plunging and working.' )
        self.OptionParser.add_option('--n_cuts', action = 'store', type = 'int', \
                dest = 'n_cuts', default = '3', help = 'Number of cuts in which	to reach depth.' )
        self.OptionParser.add_option( '--sortby', action = 'store', type = 'string', \
                dest = 'sortby', default = 'X', help = 'Which axis to sort groups by.' )
        self.OptionParser.add_option( '--rotary', action='store', type='inkbool', \
                dest = 'rotary', default = False, help = 'Output angles file and center every path over X=0' )
        self.OptionParser.add_option('--rotary-dia', action = 'store', type = 'float', \
                dest = 'rotary_dia', default = '60.0', help = 'Diameter of wheel for rotary engraving.' )
        self.OptionParser.add_option( '--groove', action='store', type='inkbool', \
                dest = 'groove', default = False, help = 'Project path on a groove.' )
        self.OptionParser.add_option('--groove-offset', action = 'store', type = 'float', \
                dest = 'groove_offset', default = '60.0', help = 'YZ offset for groove centerpoint.' )
        self.OptionParser.add_option('--groove-radius', action = 'store', type = 'float', \
                dest = 'groove_radius', default = '1.5', help = 'Radius of groove.' )
        
        self.current_pgm = 1
        
    def findPaths( self ):
        paths = []
        for dummyid, node in self.selected.iteritems():
            elements = []
            if node.tag == inkex.addNS( 'path', 'svg' ):
                for element in simplepath.parsePath( node.get( 'd' ) ):
                    if element[0].upper() not in ('M', 'L', 'Z'):
                        inkex.errormsg( 'Found a curve in path.\nAborting...' )
                        return []
                    else:
                        elements.append( element )
                        
            paths.append( elements )
            
        return paths

	#Convert x position to angle based on the rotary_dia option
    def pathAngle( self, p ):
        w = pathWidth( p )
        xpos = leftmost( p ) + (w / 2)
        pxdia = self.unittouu( "%dmm" % self.options.rotary_dia )

        return 360 * (xpos / (pxdia * math.pi))

	#Convert inkscape paths to heidenhain TNC code
    def paths2heiden( self, paths ):
        pgms = [[heiden_begin( self.current_pgm )]]
        label_no = 1
        depth = 0.0

		#Initial instructions
        if self.options.groove:
            pgms[-1].append( "FN 0 : Q0 = %+4.3f" % (self.options.groove_offset - self.options.depth) )
        else:
            pgms[-1].append( "FN 0 : Q0 = 0.000" )

        pgms[-1].append( heiden_zup( self.options.zsafe ) )
        
		#Iterate paths
        for path in paths:
			#Add label if we want to reach depth with more than one cut
            if self.options.n_cuts > 1:
                pgms[-1].append( "LBL %d" % label_no )

            if not self.options.groove:
                pgms[-1].append( "FN 2 : Q0 = +Q0 - %4.3f" % ((float( self.options.depth ) * -1.0) / float( self.options.n_cuts ) ))

			#Rotary engrave
            if self.options.rotary:
				#Center path over X0
                hcenterX( path )

            for element in path:
                x = self.uutounit( element[1][0], 'mm' )
                y = self.uutounit( element[1][1], 'mm' )

				#Moveto becomes zup, xy move
                if element[0].upper() == 'M':
                    pgms[-1].append( heiden_zup( self.options.zsafe ) )
                    pgms[-1].append( heiden_xymove( x, y, HEIDENHAIN_RAPID_FEED ) )

                    if not self.options.groove:
                        pgms[-1].append( "L Z+Q0 R F%d M" % self.options.feed )

				#Ignore Z instruction
                elif element[0].upper() == 'Z':
                    continue
				#Lineto becomes xy move
                elif element[0].upper() == 'L':
                    if self.options.rotary:
                        z = 0.4
                        pgms[-1].append( heiden_xyzmove( x, y, z, self.options.feed ) )
                    else:
                        pgms[-1].append( heiden_xymove( x, y, self.options.feed ) )

			#Add label call
            if self.options.n_cuts > 1:
                pgms[-1].append( "FN 11 : IF +Q0 GT %+4.3f GOTO LBL %d" % (self.options.depth, label_no) )
                #pgms[-1].append( "CALL LBL %d REP %d /%d" % (label_no, self.options.n_cuts - 1, self.options.n_cuts - 1) )
                label_no = (label_no + 1)

			#Reset Q0 between labels
            pgms[-1].append( "FN 0 : Q0 = 0.000" )

			#Add zup between labels
            pgms[-1].append( heiden_zup( self.options.zsafe ) )

			#Add stop if we are engraving a wheel
            if self.options.rotary:
                pgms[-1].append( "STOP M" )
                    
			#Switch to new program if current program exeeds 900 lines of code
            if len( pgms[-1] ) > 900:
                pgms[-1].append( heiden_end( self.current_pgm ) )
                self.current_pgm += 1
                pgms.append( [heiden_begin( self.current_pgm )] )
                label_no = 1
                
		#Append program end instruction
        pgms[-1].append( heiden_end( self.current_pgm ) )
        
        return pgms 
    
	#Implementation of abstract function
    def effect( self ):
        paths = self.findPaths()
        angles = []
        
        if( len( paths ) <= 0 ):
            return

        paths.sort( cmp=cmpPathsX )

        if self.options.rotary:
            for path in paths:
                angles.append( self.pathAngle( path ) )

        pgms = self.paths2heiden( paths )
        
        #Add line numbers
        for i, pgm in enumerate( pgms ):
            n = 0
            for j, line in enumerate( pgm ):
                pgms[i][j] = '%d ' % n + line
                n += 1
                
		#Print out heidenhain code
        for pgm in pgms:
            for line in pgm:
                inkex.errormsg( line )

		#Print out angles
        if self.options.rotary:
            msg = ""
            for a in angles:
                msg += "%3.3f;" % a
            inkex.errormsg( msg )
        
#Main stuff
if __name__ == '__main__':
    e = HeidengravePathToNC()
    e.affect()
