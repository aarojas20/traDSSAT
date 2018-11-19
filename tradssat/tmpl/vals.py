import numpy as np


class FileValueSet(object):

    def __init__(self):
        self._sections = {}

    def add_section(self, name):
        self._sections[name] = ValueSection(name)

    def write(self, lines, var_info):

        for s in self:
            s.write(lines, var_info)

        lines.append('')

        return lines

    def to_dict(self):
        return {name: sect.to_dict() for name, sect in self._sections.items()}

    def get_val(self, var, sect=None, subsect=None):
        if sect is not None:
            return self[sect].get_val(var, subsect)
        else:
            return next(s.get_val(var, subsect) for s in self if var in s)

    def set_val(self, var, val, sect=None, subsect=None):
        if sect is not None:
            self[sect].set_val(var, val, subsect)
        else:
            for s in self:
                if var in s:
                    s.set_val(var, val, subsect)

    def __iter__(self):
        for s in self._sections.values():
            yield s

    def __getitem__(self, item):
        return self._sections[item]


class ValueSection(object):
    def __init__(self, name):
        self.name = name
        self._subsections = []
        self._header_vars = ValueSubSection()

    def add_subsection(self, subsect):
        self._subsections.append(subsect)

    def add_header_var(self, var, val):
        self._header_vars.set_value(var, val)

    def write(self, lines, var_info):
        lines.append('*' + self.name)
        for s in self:
            s.write(lines, var_info, sect=self.name)

        lines.append('')

        return lines

    def to_dict(self):
        return [subsect.to_dict() for subsect in self]

    def get_val(self, var, subsect=None):
        val = []

        if subsect is None:
            subsect = range(len(self._subsections))
        elif isinstance(subsect, int):
            subsect = [subsect]

        for s in subsect:
            if var in s:
                val.append(s[var])

        return np.array(val).flatten()

    def set_val(self, var, val, subsect=None):

        if subsect is None:
            subsect = range(len(self._subsections))
        elif isinstance(subsect, int):
            subsect = [subsect]

        success = False
        for s in subsect:
            if var in s:
                success = True
                s[var] = val

        if not success:
            raise ValueError('Variable "{}" not found.'.format(var))

    def __iter__(self):
        for s in self._subsections:
            yield s

    def __contains__(self, item):
        return any(item in s for s in self._subsections)

    def __setitem__(self, key, value):
        for subsect in self:
            if key in subsect:
                subsect[key] = value


class ValueSubSection(object):
    def __init__(self):
        self._values = {}

    def set_value(self, var, val):
        if var not in self or (isinstance(val, np.ndarray) and (val.shape != self[var].shape)):
            self._values[var] = np.array(val)
        else:
            self[var][:] = val

    def check_dims(self):
        return len(np.unique([v.shape for v in self._values.values()])) == 1

    def check_vals(self, var_info):
        for vr in self:
            var_info.get_var(vr).check_val(self[vr])

    def n_data(self):
        self.check_dims()
        return self[list(self._values)[0]].size

    def write(self, lines, var_info, sect):
        self.check_dims()
        self.check_vals(var_info)

        lines.append('@' + ''.join([var_info.get_var(vr, sect).write() for vr in self]))
        for i in range(self.n_data()):
            line = ''.join([var_info.get_var(vr, sect).write(self[vr][i]) for vr in self])
            lines.append(line)

        return lines

    def to_dict(self):
        return self._values

    def __iter__(self):
        for vr in self._values:
            yield vr

    def __contains__(self, item):
        return item in self._values

    def __getitem__(self, item):
        return self._values[item]

    def __setitem__(self, key, value):
        self.set_value(key, value)
