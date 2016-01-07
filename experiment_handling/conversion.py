bregma_in_atlas = 5525  # in um
atlas_scale = 25 # in um


def physical_to_index(physical_coordinate):
    ind = round(physical_coordinate/atlas_scale)
    return verify_aba_index(ind)


def physical_to_bregma(physical_coordinate):
    bCoord = bregma_in_atlas - aCoord
    return um2mm(bregma_coordinate)


def bregma_to_physical(bregma_coordinate):
    bregma_coordinate  = mm2um(bCoord)
    return bregma_in_atlas - bCoord


def index_to_physical(atlas_index):
    return atlas_index*atlas_scale


def verify_aba_index(ind):
    if ind < 0:
        print "WARNING: Given physical coordinate corresponds to a negative index!"
        print "Defaulting to 0 (first slice)..."
        ind = 0
    elif ind > 528:
        print "WARNING: Given physical coordinate corresponds to an index outside of the Allen Brain Atlas space!"
        print "Defaulting to 528 (last slice)..."
        ind = 528
    return ind


def mm2um(mm):
    return mm*1000


def um2mm(um):
    return um/1000
