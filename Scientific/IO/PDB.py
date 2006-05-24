# This module handles input and output of PDB files.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# Last revision: 2006-1-11
# 

"""This module provides classes that represent PDB (Protein Data Bank)
files and configurations contained in PDB files. It provides access to
PDB files on two levels: low-level (line by line) and high-level
(chains, residues, and atoms).

Caution: The PDB file format has been heavily abused, and it is
probably impossible to write code that can deal with all variants
correctly. This modules tries to read the widest possible range of PDB
files, but gives priority to a correct interpretation of the PDB
format as defined by the Brookhaven National Laboratory.

A special problem are atom names. The PDB file format specifies that
the first two letters contain the right-justified chemical element
name. A later modification allowed the initial space in hydrogen names
to be replaced by a digit. Many programs ignore all this and treat the
name as an arbitrary left-justified four-character name. This makes it
difficult to extract the chemical element accurately; most programs
write the '"CA"' for C_alpha in such a way that it actually stands for
a calcium atom! For this reason a special element field has been added
later, but only few files use it.

The low-level routines in this module do not try to deal with the atom
name problem; they return and expect four-character atom names
including spaces in the correct positions. The high-level routines use
atom names without leading or trailing spaces, but provide and use the
element field whenever possible. For output, they use the element
field to place the atom name correctly, and for input, they construct
the element field content from the atom name if no explicit element
field is found in the file.

Except where indicated, numerical values use the same units and
conventions as specified in the PDB format description.

Example:

  >>>conf = Structure('example.pdb')
  >>>print conf
  >>>for residue in conf.residues:
  >>>    for atom in residue:
  >>>        print atom
"""

from Scientific.IO.TextFile import TextFile
from Scientific.IO.FortranFormat import FortranFormat, FortranLine
from Scientific.Geometry import Vector, Tensor
from PDBExportFilters import export_filters
import copy, string

#
# Fortran formats for PDB entries
#
atom_format = FortranFormat('A6,I5,1X,A4,A1,A4,A1,I4,A1,3X,3F8.3,2F6.2,' +
                            '6X,A4,2A2')
anisou_format = FortranFormat('A6,I5,1X,A4,A1,A4,A1,I4,A1,1X,6I7,2X,A4,2A2')
conect_format = FortranFormat('A6,11I5')
ter_format = FortranFormat('A6,I5,6X,A4,A1,I4,A1')
model_format = FortranFormat('A6,4X,I4')
header_format = FortranFormat('A6,4X,A40,A9,3X,A4')
generic_format = FortranFormat('A6,A74')

#
# Amino acid and nucleic acid residues
#
amino_acids = ['ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'CYX', 'GLN', 'GLU', 'GLY',
               'HIS', 'HID', 'HIE', 'HIP', 'HSD', 'HSE', 'HSP', 'ILE', 'LEU',
               'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL',
               'ACE', 'NME', 'NHE']

nucleic_acids = [ 'A',  'C',  'G',  'I',  'T',  'U',
                 '+A', '+C', '+G', '+I', '+T', '+U',
                  'RA',  'RC',  'RG',  'RU',
                  'DA',  'DC',  'DG',  'DT',
                  'RA5',  'RC5',  'RG5',  'RU5',
                  'DA5',  'DC5',  'DG5',  'DT5',
                  'RA3',  'RC3',  'RG3',  'RU3',
                  'DA3',  'DC3',  'DG3',  'DT3',
                  'RAN',  'RCN',  'RGN',  'RUN',
                  'DAN',  'DCN',  'DGN',  'DTN',
                  ]

def defineAminoAcidResidue(symbol):
    amino_acids.append(string.upper(symbol))

def defineNucleicAcidResidue(symbol):
    nucleic_acids.append(string.upper(symbol))


#
# Low-level file object. It represents line contents as Python dictionaries.
# For output, there are additional methods that generate sequence numbers
# for everything.
#
class PDBFile:

    """PDB file with access at the record level

    Constructor: PDBFile(|filename|, |mode|='"r"'), where |filename|
    is the file name and |mode| is '"r"' for reading and '"w"' for writing,
    The low-level file access is handled by the module
    Scientific.IO.TextFile, therefore compressed files and URLs
    (for reading) can be used as well.
    """

    def __init__(self, filename, mode = 'r', subformat = None):
        self.file = TextFile(filename, mode)
        self.output = string.lower(mode[0]) == 'w'
        self.export_filter = None
        if subformat is not None:
            export = export_filters.get(subformat, None)
            if export is not None:
                self.export_filter = export()
        self.open = 1
        if self.output:
            self.data = {'serial_number': 0,
                         'residue_number': 0,
                         'chain_id': '',
                         'segment_id': ''}
            self.het_flag = 0
            self.chain_number = -1

    def readLine(self):
        """Returns the contents of the next non-blank line (= record).
        The return value is a tuple whose first element (a string)
        contains the record type. For supported record types (HEADER,
        ATOM, HETATM, ANISOU, TERM, MODEL, CONECT), the items from the
        remaining fields are put into a dictionary which is returned
        as the second tuple element. Most dictionary elements are
        strings or numbers; atom positions are returned as a vector,
        and anisotropic temperature factors are returned as a rank-2
        tensor, already multiplied by 1.e-4. White space is stripped
        from all strings except for atom names, whose correct
        interpretation can depend on an initial space. For unsupported
        record types, the second tuple element is a string containing
        the remaining part of the record.
        """
        while 1:
            line = self.file.readline()
            if not line: return ('END','')
            if line[-1] == '\n': line = line[:-1]
            line = string.strip(line)
            if line: break
        line = string.ljust(line, 80)
        type = string.strip(line[:6])
        if type == 'ATOM' or type == 'HETATM':
            line = FortranLine(line, atom_format)
            data = {'serial_number': line[1],
                    'name': line[2],
                    'alternate': string.strip(line[3]),
                    'residue_name': string.strip(line[4]),
                    'chain_id': string.strip(line[5]),
                    'residue_number': line[6],
                    'insertion_code': string.strip(line[7]),
                    'position': Vector(line[8:11]),
                    'occupancy': line[11],
                    'temperature_factor': line[12],
                    'segment_id': string.strip(line[13]),
                    'element': string.strip(line[14]),
                    'charge': string.strip(line[15])}
            return type, data
        elif type == 'ANISOU':
            line = FortranLine(line, anisou_format)
            data = {'serial_number': line[1],
                    'name': line[2],
                    'alternate': string.strip(line[3]),
                    'residue_name': string.strip(line[4]),
                    'chain_id': string.strip(line[5]),
                    'residue_number': line[6],
                    'insertion_code': string.strip(line[7]),
                    'u': 1.e-4*Tensor([[line[8], line[11], line[12]],
                                       [line[11], line[9] , line[13]],
                                       [line[12], line[13], line[10]]]),
                    'segment_id': string.strip(line[14]),
                    'element': string.strip(line[15]),
                    'charge': string.strip(line[16])}
            return type, data
        elif type == 'TER':
            line = FortranLine(line, ter_format)
            data = {'serial_number': line[1],
                    'residue_name': string.strip(line[2]),
                    'chain_id': string.strip(line[3]),
                    'residue_number': line[4],
                    'insertion_code': string.strip(line[5])}
            return type, data
        elif type == 'CONECT':
            line = FortranLine(line, conect_format)
            data = {'serial_number': line[1],
                    'bonded': [i for i in line[2:6] if i > 0],
                    'hydrogen_bonded': [i for i in line[6:10] if i > 0],
                    'salt_bridged': [i for i in line[10:12] if i > 0]}
            return type, data
        elif type == 'MODEL':
            line = FortranLine(line, model_format)
            data = {'serial_number': line[1]}
            return type, data
        elif type == 'HEADER':
            line = FortranLine(line, header_format)
            data = {'compound': line[1],
                    'date': line[2],
                    'pdb_code': line[3]}
            return type, data
        else:
            return type, line[6:]

    def writeLine(self, type, data):
        """Writes a line using record type and data dictionary in the
        same format as returned by readLine(). Default values are
        provided for non-essential information, so the data dictionary
        need not contain all entries.
        """
        if self.export_filter is not None:
            type, data = self.export_filter.processLine(type, data)
            if type is None:
                return
        line = [type]
        if type == 'ATOM' or type == 'HETATM':
            format = atom_format
            position = data['position']
            line = line + [data.get('serial_number', 1),
                           data.get('name'),
                           data.get('alternate', ''),
                           string.rjust(data.get('residue_name', ''), 3),
                           data.get('chain_id', ''),
                           data.get('residue_number', 1),
                           data.get('insertion_code', ''),
                           position[0], position[1], position[2],
                           data.get('occupancy', 0.),
                           data.get('temperature_factor', 0.),
                           data.get('segment_id', ''),
                           string.rjust(data.get('element', ''), 2),
                           data.get('charge', '')]
        elif type == 'ANISOU':
            format = anisou_format
            u = 1.e4*data['u']
            u = [int(u[0,0]), int(u[1,1]), int(u[2,2]),
                 int(u[0,1]), int(u[0,2]), int(u[1,2])]
            line = line + [data.get('serial_number', 1),
                           data.get('name'),
                           data.get('alternate', ''),
                           string.rjust(data.get('residue_name'), 3),
                           data.get('chain_id', ''),
                           data.get('residue_number', 1),
                           data.get('insertion_code', '')] \
                        + u \
                        + [data.get('segment_id', ''),
                           string.rjust(data.get('element', ''), 2),
                           data.get('charge', '')]
        elif type == 'TER':
            format = ter_format
            line = line + [data.get('serial_number', 1),
                           string.rjust(data.get('residue_name'), 3),
                           data.get('chain_id', ''),
                           data.get('residue_number', 1),
                           data.get('insertion_code', '')]
        elif type == 'CONECT':
            format = conect_format
            line = line + [data.get('serial_number')]
            line = line + (data.get('bonded', [])+4*[None])[:4]
            line = line + (data.get('hydrogen_bonded', [])+4*[None])[:4]
            line = line + (data.get('salt_bridged', [])+2*[None])[:2]
        elif type == 'MODEL':
            format = model_format
            line = line + [data.get('serial_number')]
        elif type == 'HEADER':
            format = header_format
            line = line + [data.get('compound', ''), data.get('date', ''),
                           data.get('pdb_code')]
        else:
            format = generic_format
            line = line + [data]
        self.file.write(str(FortranLine(line, format)) + '\n')

    def writeComment(self, text):
        """Writes |text| into one or several comment lines.
        Each line of the text is prefixed with 'REMARK' and written
        to the file.
        """
        while text:
            eol = string.find(text,'\n')
            if eol == -1:
                eol = len(text)
            self.file.write('REMARK %s \n' % text[:eol])
            text = text[eol+1:]

    def writeAtom(self, name, position, occupancy=0.0, temperature_factor=0.0,
                  element=''):
        """Writes an ATOM or HETATM record using the |name|, |occupancy|,
        |temperature| and |element| information supplied. The residue and
        chain information is taken from the last calls to the methods
        nextResidue() and nextChain().
        """
        if self.het_flag:
            type = 'HETATM'
        else:
            type = 'ATOM'
        name = string.upper(name)
        if element != '' and len(element) == 1 and name and name[0] == element:
            name = ' ' + name
        self.data['name'] = name
        self.data['position'] = position
        self.data['serial_number'] = (self.data['serial_number'] + 1) % 100000
        self.data['occupancy'] = occupancy
        self.data['temperature_factor'] = temperature_factor
        self.data['element'] = element
        self.writeLine(type, self.data)

    def nextResidue(self, name, number = None, terminus = None):
        """Signals the beginning of a new residue, starting with the
        next call to writeAtom(). The residue name is |name|, and a
        |number| can be supplied optionally; by default residues in a
        chain will be numbered sequentially starting from 1. The
        value of |terminus| can be 'None', '"C"', or '"N"'; it is passed
        to export filters that can use this information in order to
        use different atom or residue names in terminal residues.
        """
        name  = string.upper(name)
        if self.export_filter is not None:
            name, number = self.export_filter.processResidue(name, number,
                                                             terminus)
        self.het_flag =  not (name in amino_acids or name in nucleic_acids)
        self.data['residue_name'] = name
        self.data['residue_number'] = (self.data['residue_number'] + 1) % 10000
        self.data['insertion_code'] = ''
        if number is not None:
            if type(number) is type(0):
                self.data['residue_number'] = number % 10000
            else:
                self.data['residue_number'] = number.number % 10000
                self.data['insertion_code'] = number.insertion_code

    def nextChain(self, chain_id = None, segment_id = ''):
        """Signals the beginning of a new chain. A chain identifier
        (string of length one) can be supplied as |chain_id|, by
        default consecutive letters from the alphabet are used.
        The equally optional |segment_id| defaults to an empty string.
        """
        if chain_id is None:
            self.chain_number = (self.chain_number + 1) % len(self._chain_ids)
            chain_id = self._chain_ids[self.chain_number]
        if self.export_filter is not None:
            chain_id, segment_id = \
                      self.export_filter.processChain(chain_id, segment_id)
        self.data['chain_id'] = (chain_id+' ')[:1]
        self.data['segment_id'] = (segment_id+'    ')[:4]
        self.data['residue_number'] = 0

    _chain_ids = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def terminateChain(self):
        "Signals the end of a chain."
        if self.export_filter is not None:
            self.export_filter.terminateChain()
        self.data['serial_number'] = (self.data['serial_number'] + 1) % 100000
        self.writeLine('TER', self.data)
        self.data['chain_id'] = ''
        self.data['segment_id'] = ''
        
    def close(self):
        """Closes the file. This method *must* be called for write mode
        because otherwise the file will be incomplete.
        """
        if self.open:
            if self.output:
                self.file.write('END\n')
            self.file.close()
            self.open = 0

    def __del__(self):
        self.close()


#
# High-level object representation of PDB file contents.
#

#
# Representation of objects.
#
class Atom:

    """Atom in a PDB structure

    Constructor: Atom(|name|, |position|, |**properties|),
    where |name| is the PDB atom name (a string),
    |position| is a atom position (a vector), and
    |properties| can include any of the other items that
    can be stored in an atom record.

    The properties can be obtained or modified using
    indexing, as for Python dictionaries.
    """
    
    def __init__(self, name, position, **properties):
        self.position = position
        self.properties = properties
        if self.properties.get('element', '') == '':
            if name[0] == ' ' or name[0] in string.digits:
                self.properties['element'] = name[1]
            elif name[1] in string.digits:
                self.properties['element'] = name[0]
        self.name = string.strip(name)

    def __getitem__(self, item):
        try:
            return self.properties[item]
        except KeyError:
            if item == 'name':
                return self.name
            elif item == 'position':
                return self.position
            else:
                raise KeyError("Undefined atom property: " + repr(item))

    def __setitem__(self, item, value):
        self.properties[item] = value

    def __str__(self):
        return self.__class__.__name__ + ' ' + self.name + \
               ' at ' + str(self.position)
    __repr__ = __str__

    def type(self):
        "Returns the six-letter record type, ATOM or HETATM."
        return 'ATOM  '

    def writeToFile(self, file):
        """Writes an atom record to |file| (a PDBFile object or a
        string containing a file name)."""
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        file.writeAtom(self.name, self.position,
                       self.properties.get('occupancy', 0.),
                       self.properties.get('temperature_factor', 0.),
                       self.properties.get('element', ''))
        if close:
            file.close()


class HetAtom(Atom):

    """HetAtom in a PDB structure

    A subclass of Atom, which differs only in the return value
    of the method type().

    Constructor: HetAtom(|name|, |position|, |**properties|).
    """

    def type(self):
        return 'HETATM'
    

class Group:

    """Atom group (residue or molecule) in a PDB file

    This is an abstract base class. Instances can be created using
    one of the subclasses (Molecule, AminoAcidResidue, NucleotideResidue).

    Group objects permit iteration over atoms with for-loops,
    as well as extraction of atoms by indexing with the
    atom name.
    """

    def __init__(self, name, atoms = None, number = None):
        self.name = name
        self.number = number
        self.atom_list = []
        self.atoms = {}
        if atoms:
            self.atom_list = atoms
            for a in atoms:
                self.atoms[a.name] = a

    def __len__(self):
        return len(self.atom_list)

    def __getitem__(self, item):
        if type(item) == type(0):
            return self.atom_list[item]
        else:
            return self.atoms[item]

    def __str__(self):
        s = self.__class__.__name__ + ' ' + self.name + ':\n'
        for atom in self.atom_list:
            s = s + '  ' + `atom` + '\n'
        return s
    __repr__ = __str__

    def isCompatible(self, residue_data):
        return residue_data['residue_name'] == self.name \
               and residue_data['residue_number'] == self.number

    def addAtom(self, atom):
        "Adds |atom| (an Atom object) to the group."
        self.atom_list.append(atom)
        self.atoms[atom.name] = atom

    def deleteAtom(self, atom):
        """Removes |atom| (an Atom object) from the group. An exception
        will be raised if |atom| is not part of the group.
        """
        self.atom_list.remove(atom)
        del self.atoms[atom.name]

    def deleteHydrogens(self):
        "Removes all hydrogen atoms."
        delete = []
        for a in self.atom_list:
            if a.name[0] == 'H' or (a.name[0] in string.digits
                                    and a.name[1] == 'H'):
                delete.append(a)
        for a in delete:
            self.deleteAtom(a)

    def changeName(self, name):
        "Sets the PDB residue name to |name|."
        self.name = name

    def writeToFile(self, file):
        """Writes the group to |file| (a PDBFile object or a
        string containing a file name).
        """
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        file.nextResidue(self.name, self.number, None)
        for a in self.atom_list:
            a.writeToFile(file)
        if close:
            file.close()

class Molecule(Group):

    """Molecule in a PDB file

    A subclass of Group.

    Constructor: Molecule(|name|, |atoms|='None', |number|=None),
    where |name| is the PDB residue name. An optional list
    of |atoms| can be specified, otherwise the molecule is initially
    empty. The optional |number| is the PDB residue number.

    Note: In PDB files, non-chain molecules are treated as residues,
    there is no separate molecule definition. This modules defines
    every residue as a molecule that is not an amino acid residue or a
    nucleotide residue.
    """

    pass

class Residue(Group):

    pass

class AminoAcidResidue(Residue):

    """Amino acid residue in a PDB file

    A subclass of Group.

    Constructor: AminoAcidResidue(|name|, |atoms|='None', |number|=None),
    where |name| is the PDB residue name. An optional list
    of |atoms| can be specified, otherwise the residue is initially
    empty. The optional |number| is the PDB residue number.
    """

    is_amino_acid = 1

    def isCTerminus(self):
        """Returns 1 if the residue is in C-terminal configuration,
        i.e. if it has a second oxygen bound to the carbon atom of
        the peptide group.
        """
        return self.atoms.has_key('OXT') or self.atoms.has_key('OT2')

    def isNTerminus(self):
        """Returns 1 if the residue is in N-terminal configuration,
        i.e. if it contains more than one hydrogen bound to be
        nitrogen atom of the peptide group.
        """
        return self.atoms.has_key('1HT') or self.atoms.has_key('2HT') \
               or self.atoms.has_key('3HT')

    def writeToFile(self, file):
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        terminus = None
        if self.isCTerminus(): terminus = 'C'
        if self.isNTerminus(): terminus = 'N'
        file.nextResidue(self.name, self.number, terminus)
        for a in self.atom_list:
            a.writeToFile(file)
        if close:
            file.close()


class NucleotideResidue(Residue):

    """Nucleotide residue in a PDB file

    A subclass of Group.

    Constructor: NucleotideResidue(|name|, |atoms|='None', |number|=None),
    where |name| is the PDB residue name. An optional list
    of |atoms| can be specified, otherwise the residue is initially
    empty. The optional |number| is the PDB residue number.
    """

    is_nucleotide = 1

    def __init__(self, name, atoms = None, number = None):
        self.pdbname = name
        name = string.strip(name)
        if name[0] != 'D' and name[0] != 'R':
            name = 'D' + name
        Residue.__init__(self, name, atoms, number)
        for a in atoms:
            if a.name == 'O2*' or a.name == "O2'": # Ribose
                self.name = 'R' + self.name[1:]

    def isCompatible(self, residue_data):
        return (residue_data['residue_name'] == self.name or
                residue_data['residue_name'] == self.pdbname) \
               and residue_data['residue_number'] == self.number

    def addAtom(self, atom):
        Residue.addAtom(self, atom)
        if atom.name == 'O2*' or atom.name == "O2'": # Ribose
            self.name = 'R' + self.name[1:]

    def hasRibose(self):
        "Returns 1 if the residue has an atom named O2*."
        return self.atoms.has_key('O2*') or self.atoms.has_key("O2'")

    def hasDesoxyribose(self):
        "Returns 1 if the residue has no atom named O2*."
        return not self.hasRibose()

    def hasPhosphate(self):
        "Returns 1 if the residue has a phosphate group."
        return self.atoms.has_key('P')

    def hasTerminalH(self):
        "Returns 1 if the residue has a 3-terminal H atom."
        return self.atoms.has_key('H3T')

    def writeToFile(self, file):
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        terminus = None
        if not self.hasPhosphate(): terminus = '5'
        file.nextResidue(self.name[1:], self.number, terminus)
        for a in self.atom_list:
            a.writeToFile(file)
        if close:
            file.close()

class Chain:

    """Chain of PDB residues

    This is an abstract base class. Instances can be created using
    one of the subclasses (PeptideChain, NucleotideChain).

    Chain objects respond to len() and return their residues
    by indexing with integers.
    """

    def __init__(self, residues = None, chain_id = None, segment_id = None):
        if residues is None:
            self.residues = []
        else:
            self.residues = residues
        self.chain_id = chain_id
        self.segment_id = segment_id

    def __len__(self):
        return len(self.residues)

    def sequence(self):
        "Returns the list of residue names."
        return [r.name for r in self.residues]

    def __getitem__(self, index):
        return self.residues[index]

    def addResidue(self, residue):
        "Add |residue| at the end of the chain."
        self.residues.append(residue)

    def removeResidues(self, first, last):
        """Remove residues starting from |first| up to (but not
        including) |last|. If |last| is 'None', remove everything
        starting from |first|.
        """
        if last is None:
            del self.residues[first:]
        else:
            del self.residues[first:last]

    def deleteHydrogens(self):
        "Removes all hydrogen atoms."
        for r in self.residues:
            r.deleteHydrogens()

    def writeToFile(self, file):
        """Writes the chain to |file| (a PDBFile object or a
        string containing a file name).
        """
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        file.nextChain(self.chain_id, self.segment_id)
        for r in self.residues:
            r.writeToFile(file)
        file.terminateChain()
        if close:
            file.close()

class PeptideChain(Chain):

    """Peptide chain in a PDB file

    A subclass of Chain.
    
    Constructor: PeptideChain(|residues|='None', |chain_id|='None',
                              |segment_id|='None'), where |chain_id|
    is a one-letter chain identifier and |segment_id| is
    a multi-character chain identifier, both are optional. A list
    of AminoAcidResidue objects can be passed as |residues|; by
    default a peptide chain is initially empty.
    """

    def __getslice__(self, i1, i2):
        return self.__class__(self.residues[i1:i2])

    def isTerminated(self):
        "Returns 1 if the last residue is in C-terminal configuration."
        return self.residues and self.residues[-1].isCTerminus()

    def isCompatible(self, chain_data, residue_data):
        return chain_data['chain_id'] == self.chain_id and \
               chain_data['segment_id'] == self.segment_id and \
               residue_data['residue_name'] in amino_acids


class NucleotideChain(Chain):

    """Nucleotide chain in a PDB file

    A subclass of Chain.
    
    Constructor: NucleotideChain(|residues|='None', |chain_id|='None',
                                 |segment_id|='None'), where |chain_id|
    is a one-letter chain identifier and |segment_id| is
    a multi-character chain identifier, both are optional. A list
    of NucleotideResidue objects can be passed as |residues|; by
    default a nucleotide chain is initially empty.
    """

    def __getslice__(self, i1, i2):
        return self.__class__(self.residues[i1:i2])

    def isTerminated(self):
        # impossible to detect for standard PDB files, but we can still
        # do something useful for certain non-standard files
        return self.residues and \
               (self.residues[-1].name[-1] == '3'
                or self.residues[-1].hasTerminalH())

    def isCompatible(self, chain_data, residue_data):
        return chain_data['chain_id'] == self.chain_id and \
               chain_data['segment_id'] == self.segment_id and \
               residue_data['residue_name'] in nucleic_acids

class DummyChain(Chain):

    def __init__(self, structure, chain_id, segment_id):
        self.structure = structure
        self.chain_id = chain_id
        self.segment_id = segment_id

    def isTerminated(self):
        return 0

    def addResidue(self, residue):
        self.structure.addMolecule(residue)

    def isCompatible(self, chain_data, residue_data):
        return chain_data['chain_id'] == self.chain_id and \
               chain_data['segment_id'] == self.segment_id and \
               residue_data['residue_name'] not in amino_acids and \
               residue_data['residue_name'] not in nucleic_acids

#
# Residue number class for dealing with insertion codes
#
class ResidueNumber:

    """PDB residue number

    Most PDB residue numbers are simple integers, but when insertion
    codes are used a number can consist of an integer plus a letter.
    Such compound residue numbers are represented by this class.

    Constructor: ResidueNumber(|number|, |insertion_code|)
    """

    def __init__(self, number, insertion_code):
        self.number = number
        self.insertion_code = insertion_code

    def __cmp__(self, other):
        if type(other) == type(0):
            if self.number == other:
                return 1
            else:
                return cmp(self.number, other)
        if self.number == other.number:
            return cmp(self.insertion_code, other.insertion_code)
        else:
            return cmp(self.number, other.number)

    def __str__(self):
        return str(self.number) + self.insertion_code
    __repr__ = __str__

#
# The configuration class.
#
class Structure:

    """A high-level representation of the contents of a PDB file

    Constructor: Structure(|filename|, |model|='0', |alternate_code|='"A"'),
    where |filename| is the name of the PDB file. Compressed files
    and URLs are accepted, as for class PDBFile. The two optional
    arguments specify which data should be read in case of a
    multiple-model file or in case of a file that contains alternative
    positions for some atoms.

    The components of a system can be accessed in several ways
    ('s' is an instance of this class):

    - 's.residues' is a list of all PDB residues, in the order in
      which they occurred in the file.

    - 's.peptide_chains' is a list of PeptideChain objects, containing
      all peptide chains in the file in their original order.

    - 's.nucleotide_chains' is a list of NucleotideChain objects, containing
      all nucleotide chains in the file in their original order.

    - 's.molecules' is a list of all PDB residues that are neither
      amino acid residues nor nucleotide residues, in their original
      order.

    - 's.objects' is a list of all high-level objects (peptide chains,
      nucleotide chains, and molecules) in their original order.

    An iteration over a Structure instance by a for-loop is equivalent
    to an iteration over the residue list.
    """

    def __init__(self, filename, model = 0, alternate_code = 'A'):
        self.filename = filename
        self.model = model
        self.alternate = alternate_code
        self.pdb_code = ''
        self.residues = []
        self.objects = []
        self.peptide_chains = []
        self.nucleotide_chains = []
        self.molecules = {}
        self.parseFile(PDBFile(filename))

    peptide_chain_constructor = PeptideChain
    nucleotide_chain_constructor = NucleotideChain
    molecule_constructor = Molecule

    def __len__(self):
        return len(self.residues)

    def __getitem__(self, item):
        return self.residues[item]

    def deleteHydrogens(self):
        "Removes all hydrogen atoms."
        for r in self.residues:
            r.deleteHydrogens()

    def splitPeptideChain(self, number, position):
        """Splits the peptide chain indicated by |number| (0 being
        the first peptide chain in the PDB file) after the residue indicated
        by |position| (0 being the first residue of the chain).
        The two chain fragments remain adjacent in the peptide chain
        list, i.e. the numbers of all following nucleotide chains increase
        by one.
        """
        self._splitChain(self.peptide_chain_constructor,
                         self.peptide_chains, number, position)
        
    def splitNucleotideChain(self, number, position):
        """Splits the nucleotide chain indicated by |number| (0 being
        the first nucleotide chain in the PDB file) after the residue indicated
        by |position| (0 being the first residue of the chain).
        The two chain fragments remain adjacent in the nucleotide chain
        list, i.e. the numbers of all following nucleotide chains increase
        by one.
        """
        self._splitChain(self.nucleotide_chain_constructor,
                         self.nucleotide_chains, number, position)

    def _splitChain(self, constructor, chain_list, number, position):
        chain = chain_list[number]
        part1 = constructor(chain.residues[:position],
                            chain.chain_id, chain.segment_id)
        part2 = constructor(chain.residues[position:])
        chain_list[number:number+1] = [part1, part2]
        index = self.objects.index(chain)
        self.objects[index:index+1] = [part1, part2]

    def joinPeptideChains(self, first, second):
        """Join the two peptide chains indicated by |first| and |second|
        into one peptide chain. The new chain occupies the position
        |first|; the chain at |second| is removed from the peptide
        chain list.
        """
        self._joinChains(self.peptide_chain_constructor,
                         self.peptide_chains, first, second)
        
    def joinNucleotideChains(self, first, second):
        """Join the two nucleotide chains indicated by |first| and |second|
        into one nucleotide chain. The new chain occupies the position
        |first|; the chain at |second| is removed from the nucleotide
        chain list.
        """
        self._joinChains(self.nucleotide_chain_constructor,
                         self.nucleotide_chains, first, second)

    def _joinChains(self, constructor, chain_list, first, second):
        chain1 = chain_list[first]
        chain2 = chain_list[second]
        total = constructor(chain1.residues+chain2.residues,
                            chain1.chain_id, chain1.segment_id)
        chain_list[first] = total
        del chain_list[second]
        index = self.objects.index(chain1)
        self.objects[index] = total
        index = self.objects.index(chain2)
        del self.objects[index]

    def addMolecule(self, molecule):
        try:
            molecule_list = self.molecules[molecule.name]
        except KeyError:
            molecule_list = []
            self.molecules[molecule.name] = molecule_list
        molecule_list.append(molecule)
        self.objects.append(molecule)

    def extractData(self, data):
        atom_data = {}
        for name in ['serial_number', 'name', 'position',
                     'occupancy', 'temperature_factor']:
            atom_data[name] = data[name]
        for name in ['alternate', 'charge']:
            value = data[name]
            if value:
                atom_data[name] = value
        element = data['element']
        if element != '':
            try:
                string.atoi(element)
            except ValueError:
                atom_data['element'] = element
        residue_data = {'residue_name': data['residue_name']}
        number = data['residue_number']
        insertion = data['insertion_code']
        if insertion == '':
            residue_data['residue_number'] = number
        else:
            residue_data['residue_number'] = ResidueNumber(number, insertion)
        chain_data = {}
        for name in ['chain_id', 'segment_id']:
            chain_data[name] = data[name]
        if chain_data['segment_id'] == self.pdb_code:
            chain_data['segment_id'] = ''
        return atom_data, residue_data, chain_data

    def newResidue(self, residue_data):
        name = residue_data['residue_name']
        residue_number = residue_data['residue_number']
        if name in amino_acids:
            residue = AminoAcidResidue(name, [], residue_number)
        elif name in nucleic_acids:
            residue = NucleotideResidue(name, [], residue_number)
        else:
            residue = self.molecule_constructor(name, [], residue_number)
        self.residues.append(residue)
        return residue

    def newChain(self, residue, chain_data):
        if hasattr(residue, 'is_amino_acid'):
            chain = self.peptide_chain_constructor([], chain_data['chain_id'],
                                                   chain_data['segment_id'])
            self.peptide_chains.append(chain)
            self.objects.append(chain)
        elif hasattr(residue, 'is_nucleotide'):
            chain = self.nucleotide_chain_constructor([],
                                                      chain_data['chain_id'],
                                                      chain_data['segment_id'])
            self.nucleotide_chains.append(chain)
            self.objects.append(chain)
        else:
            chain = DummyChain(self, chain_data['chain_id'],
                               chain_data['segment_id'])
        return chain

    def parseFile(self, file):
        atom = None
        residue = None
        chain = None
        read = self.model == 0
        while 1:
            type, data = file.readLine()
            if type == 'END': break
            elif type == 'HEADER':
                self.pdb_code = data['pdb_code']
            elif type == 'MODEL':
                read = data['serial_number'] == self.model
                if self.model == 0 and len(self.residues) == 0:
                    read = 1
            elif type == 'ENDMDL':
                read = 0
            elif read:
                if type == 'ATOM' or type == 'HETATM':
                    alt = data['alternate']
                    if alt == '' or alt == self.alternate:
                        atom_data, residue_data, chain_data = \
                                   self.extractData(data)
                        if type == 'ATOM':
                            atom = apply(Atom, (), atom_data)
                        else:
                            atom = apply(HetAtom, (), atom_data)
                        new_chain = chain is None or \
                                    not chain.isCompatible(chain_data,
                                                           residue_data)
                        new_residue = new_chain or residue is None \
                                      or not residue.isCompatible(residue_data)
                        if new_residue and chain is not None and \
                           chain.isTerminated():
                            new_chain = 1
                        if new_residue:
                            residue = self.newResidue(residue_data)
                            if new_chain:
                                chain = self.newChain(residue, chain_data)
                            chain.addResidue(residue)
                        residue.addAtom(atom)
                elif type == 'ANISOU':
                    alt = data['alternate']
                    if alt == '' or alt == self.alternate:
                        if atom is None:
                            raise ValueError("ANISOU record before " +
                                              "ATOM record")
                        atom['u'] = data['u']
                elif type == 'TERM':
                    if chain is None:
                        raise ValueError("TERM record before chain")
                    chain = None

    def renumberAtoms(self):
        "Renumber all atoms sequentially starting with 1."
        n = 0
        for residue in self.residues:
            for atom in residue:
                atom['serial_number'] = n
                n = n + 1

    def __repr__(self):
        s = self.__class__.__name__ + "(" + repr(self.filename)
        if self.model != 0:
            s = s + ", model=" + repr(self.model)
        if self.alternate != 'A':
            s = s + ", alternate_code = " + repr(self.alternate_code)
        s = s + "):\n"
        for name, list in [("Peptide", self.peptide_chains),
                           ("Nucleotide", self.nucleotide_chains)]:
            for c in list:
                s = s + "  " + name + " chain "
                if c.segment_id:
                    s = s + c.segment_id + " "
                elif c.chain_id:
                    s = s + c.chain_id + " "
                s = s + "of length " + repr(len(c)) + "\n"
        for name, list in self.molecules.items():
            s = s + "  " + repr(len(list)) + " " + name + " molecule"
            if len(list) == 1:
                s = s + "\n"
            else:
                s = s + "s\n"
        return s

    def writeToFile(self, file):
        """Writes all objects to |file| (a PDBFile object or a
        string containing a file name).
        """
        close = 0
        if type(file) == type(''):
            file = PDBFile(file, 'w')
            close = 1
        for o in self.objects:
            o.writeToFile(file)
        if close:
            file.close()

if __name__ == '__main__':

    if 0:

        file = PDBFile('~/3lzt.pdb')
        copy = PDBFile('test.pdb', 'w', 'xplor')
        while 1:
            type, data = file.readLine()
            if type == 'END':
                break
            copy.writeLine(type, data)
        copy.close()

    if 1:

        s = Structure('~/1C1C.pdb')
        #s = Structure('./3lzt.pdb')
        #s = Structure('~/1tka.pdb')
        print s
