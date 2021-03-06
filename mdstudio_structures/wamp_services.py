# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import sys
import os
import tempfile

from autobahn.wamp import RegisterOptions
from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession

from Bio.PDB import PDBList
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.PDBParser import PDBParser

from mdstudio_structures import toolkits
from mdstudio_structures.cheminfo_wamp.cheminfo_descriptors_wamp import CheminfoDescriptorsWampApi
from mdstudio_structures.cheminfo_wamp.cheminfo_molhandle_wamp import CheminfoMolhandleWampApi
from mdstudio_structures.cheminfo_wamp.cheminfo_fingerprints_wamp import CheminfoFingerprintsWampApi

# Library and function compatibility
if sys.version_info[0] < 3:
    from cStringIO import StringIO
else:
    from io import StringIO


class StructuresWampApi(
        CheminfoDescriptorsWampApi, CheminfoMolhandleWampApi,
        CheminfoFingerprintsWampApi, ComponentSession):
    """
    Structure database WAMP methods.
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('chemical_similarity', 'chemical_similarity_request', 'chemical_similarity_response',
              options=RegisterOptions(invoke=u'roundrobin'))
    def calculate_chemical_similarity(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).calculate_chemical_similarity(request, claims)

    @endpoint('descriptors', 'descriptors_request', 'descriptors_response',
              options=RegisterOptions(invoke=u'roundrobin'))
    def get_descriptors(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).get_descriptors(request, claims)

    @endpoint('convert', 'convert_request', 'convert_response', options=RegisterOptions(invoke=u'roundrobin'))
    def convert_structures(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).convert_structures(request, claims)

    @endpoint('addh', 'addh_request', 'addh_response', options=RegisterOptions(invoke=u'roundrobin'))
    def addh_structures(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).addh_structures(request, claims)

    @endpoint('removeh', 'removeh_request', 'removeh_response', options=RegisterOptions(invoke=u'roundrobin'))
    def removeh_structures(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).removeh_structures(request, claims)

    @endpoint('make3d', 'make3d_request', 'make3d_response', options=RegisterOptions(invoke=u'roundrobin'))
    def make3d_structures(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).make3d_structures(request, claims)

    @endpoint('info', 'info_request', 'info_response', options=RegisterOptions(invoke=u'roundrobin'))
    def structure_attributes(self, request, claims):
        return super(StructuresWampApi, self).structure_attributes(request, claims)

    @endpoint('rotate', 'rotate_request', 'rotate_response', options=RegisterOptions(invoke=u'roundrobin'))
    def rotate_structures(self, request, claims):
        request['workdir'] = os.path.abspath(request['workdir'])
        return super(StructuresWampApi, self).rotate_structures(request, claims)

    @endpoint('supported_toolkits', 'supported_toolkits_request', 'supported_toolkits_response',
              options=RegisterOptions(invoke=u'roundrobin'))
    def supported_toolkits(self, request, claims):
        """
        Query available toolkits.

        For a detailed input description see the file:
           mdstudio_structures/schemas/endpoints/supported_toolkits_request_v1.json
        And for a detailed description of the output see:
           mdstudio_structures/schemas/endpoints/supported_toolkits_response_v1.json
        """
        return {'status': 'completed', 'toolkits': list(toolkits.keys())}

    @endpoint('remove_residues', 'remove_residues_request', 'remove_residues_response',
              options=RegisterOptions(invoke=u'roundrobin'))
    def remove_residues(self, request, claims):
        """
        Remove residues from a PDB structure

        For a detailed input description see the file:
           mdstudio_structures/schemas/endpoints/removed_residues_request_v1.json
        And for a detailed description of the output see:
           mdstudio_structures/schemas/endpoints/removed_residues_response_v1.json
        """
        request['workdir'] = os.path.abspath(request['workdir'])
        # Parse the structure
        parser = PDBParser(PERMISSIVE=True)
        struc_obj = StringIO(request.get('mol'))

        structure = parser.get_structure('mol_object', struc_obj)
        struc_obj.close()

        to_remove = [r.upper() for r in request.get('residues', [])]
        removed = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    if residue.get_resname() in to_remove:
                        chain.detach_child(residue.id)
                        removed.append(residue.get_resname())
                if len(chain) == 0:
                    model.detach_child(chain.id)
        self.log.info('Removed residues: {0}'.format(','.join(removed)))

        # Save to file or string
        pdbio = PDBIO()
        pdbio.set_structure(structure)

        status = 'completed'
        if request.get('workdir'):
            result = os.path.join(request.get('workdir'), 'structure.pdb')
            pdbio.save(result)
        else:
            outfile = StringIO()
            pdbio.save(outfile)
            outfile.seek(0)
            result = outfile.read()

        return {'status': status, 'mol': result}

    @endpoint('retrieve_rcsb_structure', 'retrieve_rcsb_structure_request', 'retrieve_rcsb_structure_response',
              options=RegisterOptions(invoke=u'roundrobin'))
    def fetch_rcsb_structure(self, request, claims):
        """
        Download a structure file from the RCSB database using a PDB ID

        For a detailed input description see the file:
           mdstudio_structures/schemas/endpoints/retrieve_rcsb_structures_request_v1.json
        And for a detailed description of the output see:
           mdstudio_structures/schemas/endpoints/retrieve_rcsb_structures_response_v1.json
        """
        # Create workdir and save file
        request['workdir'] = os.path.abspath(request['workdir'])
        workdir = os.path.join(request.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.makedirs(workdir)

        # Retrieve the PDB file
        pdb_id = request['pdb_id'].upper()
        pdb = PDBList()
        dfile = pdb.retrieve_pdb_file(
            pdb_id, file_format=request.get('rcsb_file_format', 'pdb'), pdir=workdir,
            overwrite=True)

        # Change file extension
        base, ext = os.path.splitext(dfile)
        ext = ext.lstrip('.')
        if ext == 'ent':
            os.rename(dfile, '{0}.pdb'.format(base))
            dfile = '{0}.pdb'.format(base)

        # Return file path if workdir in function arguments else return
        # file content inline.
        if os.path.isfile(dfile):
            status = 'completed'
            if 'workdir' in request:
                molecule = dfile
            else:
                with open(dfile, 'r') as f:
                    molecule = f.read()

        else:
            self.log.error('Unable to download structure: {0}'.format(pdb_id))
            status = 'failed'
            molecule = None

        result = {'path': None, 'content': molecule, 'extension': ext}

        return {'status': status, 'mol': result}
