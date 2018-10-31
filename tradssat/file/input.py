import numpy as np

from tradssat.file.var import Variable, VariableSet


class InpFile(object):
    ext = None

    def __init__(self, file):
        self.file = file
        self.var_info = VariableSet(self._get_var_info())
        self.template = self._get_template()

        self.values = FileValueSet()
        self._read()

    def _read(self):

        with open(self.file, encoding='utf8') as f:
            block = []  # To store lines that go in the same section
            for l in f.readlines():

                if l[0] == '!':  # skip comments
                    continue

                if l[0] == '*':  # start of section
                    self._read_section_vars(l)

                    # Process any previously stored block
                    if len(block):
                        self._read_section(block)

                    # Clear the current block
                    block.clear()

                elif len(l.strip()):
                    block.append(l)  # Append current line to block

            # Read the last block too
            self._read_section(block)

    def write(self, file, check=True):
        lines = []

        for sect_line, subs in self.template.items():
            lines.append(sect_line)

            for sub_line, sub_templt in subs:
                lines.append(sub_line)
                var_names = self._get_var_names(sub_line)
                dims = [self.get_dims_val(vr) for vr in var_names]
                if not np.unique(dims).size == 1:
                    raise ValueError(
                        'Not all variables in the same subsection have the same dimensions:'
                        '\n\t{}'.format(', '.join([f'{vr}: {dm}' for vr, dm in zip(var_names, dims)]))
                    )
                dims = self.get_dims_val(var_names[0])
                if check:
                    for vr in var_names:
                        rng = self.get_var_lims(vr)
                        val = self.get_val(vr)
                        if rng is not None:
                            errs = np.where(np.logical_or(np.greater(val, rng[1]), np.less(val, rng[0])))
                            if len(errs):
                                raise ValueError(
                                    f'Variable {vr} out of bounds at values: {val[errs]}!'
                                )

                for i in range(dims):
                    d_vals = {}
                    for vr in var_names:
                        d_vals[vr] = self.get_val(vr)[i]
                    lines.append(sub_templt.format(**d_vals))

            lines.append('')

        with open(file, encoding='utf8') as f:
            f.writelines(lines)

    def get_val(self, var):
        return self.values[var]['val']

    def get_dims_val(self, var):
        return self.get_val(var).shape

    def set_var(self, var, val):
        if isinstance(val, np.ndarray) and val.shape != self.get_dims_val(var):
            self.values[var] = val
        else:
            self.values[var][:] = val

    def get_var_section(self, var):
        return self.var_info[var].sect

    def get_var_type(self, var):
        return self.var_info[var].type_

    def get_var_size(self, var):
        return self.var_info[var].size

    def get_var_lims(self, var):
        return self.var_info[var].lims

    def _read_section(self, block):
        section_name = self._get_sect_name(block[0])
        self.values.add_section(section_name)

        subblock = []
        for l in block:
            if l[0] == '@':

                if len(subblock):
                    self._read_subsection(section_name, subblock)
                subblock.clear()

            # Append current line to section
            if len(l.strip()):
                subblock.append(l)

        self._read_subsection(section_name, subblock)

    def _read_subsection(self, section_name, subblock):
        var_names = self._get_var_names(subblock[0])
        n_lines = len(subblock) - 1  # -1 for the header line (with "@" )
        cum_len = np.cumsum([0] + [self.get_var_size(vr) for vr in var_names])
        cutoffs = [(cum_len[i], cum_len[i + 1]) for i in range(len(var_names))]

        d_vals = {vr: self._gen_empty_mtrx(vr, n_lines) for vr in var_names}

        for i, l in enumerate(subblock[1:]):
            vals = [l[c[0]:c[1]] for c in cutoffs]
            for vr, vl in zip(var_names, vals):
                d_vals[i] = vl

        for vr in var_names:
            self.values[section_name][vr] = d_vals[vr]

    def _read_section_vars(self, l):
        pass

    def _gen_empty_mtrx(self, var, size):
        tp = self.get_var_type(var)
        if tp == 'float':
            dtype = float
        elif tp == 'int':
            dtype = int
        elif tp == 'str':
            size = self.get_var_size(var)
            dtype = f'U{size}'
        else:
            dtype = tp

        return np.empty(size, dtype=dtype)

    @staticmethod
    def _get_sect_name(line):
        return line[1:].strip()

    @staticmethod
    def _get_var_names(line):
        return line[1:].split()  # skip initial "@"

    def _get_var_info(self):
        """
        Return a dictionary of variable information.

        Returns
        -------
        set[Variable]
        """

        raise NotImplementedError

    def _get_template(self):
        raise NotImplementedError


class FileValueSet(object):
    def __init__(self):
        self._sections = {}

    def add_section(self, name):
        self._sections[name] = ValueSection

    def __getitem__(self, item):
        return self._sections[item]


class ValueSection(object):
    def __init__(self):
        self._values = {}

    def set_value(self, var, val):
        pass

    def check(self):
        return len(np.unique([v.shape for v in self._values.values()])) == 1

    def __getitem__(self, item):
        return self._values[item]

    def __setitem__(self, key, value):
        self.set_value(key, value)
