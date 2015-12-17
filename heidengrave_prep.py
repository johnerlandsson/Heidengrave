import inkex
import bezmisc
import cubicsuperpath
import math
import simplepath

def tpoint( (x1,y1), (x2,y2), t = 0.5 ):
    return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]

def cspbezsplit( sp1, sp2, t = 0.5 ):
    m1 = tpoint( sp1[1], sp1[2], t )
    m2 = tpoint( sp1[2], sp2[0], t )
    m3 = tpoint( sp2[0], sp2[1], t )
    m4 = tpoint( m1, m2, t )
    m5 = tpoint( m2, m3, t )
    m = tpoint( m4, m5, t )

    return [[sp1[0][:],sp1[1][:],m1], [m4,m,m5], [m3,sp2[1][:],sp2[2][:]]]

def cspbezsplitatlength( sp1, sp2, l = 0.5, tolerance = 0.001 ):
    bez = ( sp1[1][:],sp1[2][:],sp2[0][:],sp2[1][:] )
    t = bezmisc.beziertatlength( bez, l, tolerance )

    return cspbezsplit( sp1, sp2, t )

def cspseglength( sp1, sp2, tolerance = 0.001 ):
    bez = (sp1[1][:], sp1[2][:], sp2[0][:], sp2[1][:])
    return bezmisc.bezierlength( bez, tolerance )


class PrepForHeidengraveEffect( inkex.Effect ):
    def __init__( self ):
        #Call base class constructior
        inkex.Effect.__init__( self )

        #Create parameters
        self.OptionParser.add_option( '--split-segments', action='store', type='inkbool', \
                dest = 'split_segments', default = False, help = 'Do you want to set a maximum length for segments?')
        self.OptionParser.add_option('--max-length', action = 'store', type = 'float', \
                dest = 'max_length', default = '0.2', help = 'Maximum length of segment.')
        self.OptionParser.add_option('--curve-precision', action = 'store', type = 'float', \
                dest = 'curve_precision', default = '1.0', help = 'Curve precision.')
        
    def splitSegments( self ):
        #Read max_length parameter
        max_length = self.options.max_length
        
        for dummyid, node in self.selected.iteritems():
            if node.tag == inkex.addNS( 'path', 'svg' ):
                p = cubicsuperpath.parsePath( node.get( 'd' ) )

                new = []
                for sub in p:
                    new.append( [sub[0][:]] )
                    i = 1
                    while i <= len( sub ) -1:
                        length = cspseglength( new[-1][-1], sub[i] )
                        splits = math.ceil( length / max_length )

                        for s in xrange( int(splits), 1, -1 ):
                            new[-1][-1], next, sub[i] = cspbezsplitatlength( new[-1][-1], sub[i], 1.0 / s )
                            new[-1].append( next[:] )

                        new[-1].append( sub[i] )
                        i += 1
                node.set( 'd', cubicsuperpath.formatPath( new ) )
                
    def splitCurves( self ):
        smoothness = self.options.curve_precision
        
        for dummyid, node in self.selected.iteritems():
            if node.tag == inkex.addNS( 'path', 'svg' ):
                for element in simplepath.parsePath( node.get( 'd' ) ):
                    if element[0].upper() == 'C':
                        csp = cubicsuperpath.CubicSuperPath( element )
                        curve = (element[1][0], element[1][1])
                        inkex.errormsg( str( curve ) )
                
                

    def effect(self):
        #Make sure there are objects selected
        if len( self.selected ) <= 0:
            inkex.errormsg( 'No paths selected' )
            return
        
        self.splitCurves()
        
        if self.options.split_segments:
            self.splitSegments()


if __name__ == '__main__':
    effect = PrepForHeidengraveEffect()
    effect.affect()