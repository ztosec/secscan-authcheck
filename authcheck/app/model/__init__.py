class BasicModel(dict):
    def filter_keys(self, *keys):
        rest = {}
        for k, v in self.items():
            if k not in keys:
                rest[k] = v
        return rest

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, item):
        if item == '__getstate__':  # 序列化
            return self.__getattribute__('__getstate__')
        return self.get(item)
