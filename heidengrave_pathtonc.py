import inkex
import simplepath

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
    
    def paths2heiden( self, paths ):
        pgms = [[heiden_begin( self.current_pgm )]]
        
        for path in paths:
            for element in path:
                if element[0].upper() == 'M':
                    pgms[-1].append( heiden_zup( self.options.zsafe ) )
                    pgms[-1].append( heiden_xymove( self.uutounit( element[1][0], 'mm' ), 
                        self.uutounit( element[1][1], 'mm' ), self.options.feed ) )
                    pgms[-1].append( heiden_zmove( self.options.depth, self.options.feed ) )
                elif element[0].upper() == 'Z':
                    continue
                elif element[0].upper() == 'L':
                    pgms[-1].append( heiden_xymove( self.uutounit( element[1][0], 'mm' ), 
                        self.uutounit( element[1][1], 'mm' ), self.options.feed ) )
                    
            if len( pgms[-1] ) > 900:
                pgms[-1].append( heiden_end( self.current_pgm ) )
                self.current_pgm += 1
                pgms.append( [heiden_begin( self.current_pgm )] )
                
        pgms[-1].append( heiden_zup( self.options.zsafe ) )
        pgms[-1].append( heiden_end( self.current_pgm ) )
        
        return pgms 
    
    def effect( self ):
        paths = self.findPaths()
        
        if( len( paths ) <= 0 ):
            return
        
        pgms = self.paths2heiden( paths )
        
        #Add line numbers
        for i, pgm in enumerate( pgms ):
            n = 0
            for j, line in enumerate( pgm ):
                pgms[i][j] = '%d ' % n + line
                n += 1
                
        for pgm in pgms:
            for line in pgm:
                inkex.errormsg( line )
        
if __name__ == '__main__':
    e = HeidengravePathToNC()
    e.affect()