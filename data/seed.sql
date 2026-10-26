-- 虚构的便利店商品数据（演示用）
CREATE TABLE products (
    id        TEXT PRIMARY KEY,   -- 商品编号
    name_ja   TEXT NOT NULL,
    name_zh   TEXT NOT NULL,
    name_en   TEXT NOT NULL,
    category  TEXT NOT NULL,      -- food / drink / daily / electronics
    price_jpy INTEGER NOT NULL,   -- 含税价格（日元）
    stock     INTEGER NOT NULL,   -- 当前库存
    shelf     TEXT NOT NULL       -- 货架位置
);

INSERT INTO products VALUES
('F001', 'おにぎり 鮭',        '饭团（三文鱼）',     'Rice ball (salmon)',        'food',        160, 12, 'A-1'),
('F002', 'おにぎり ツナマヨ',  '饭团（金枪鱼蛋黄酱）', 'Rice ball (tuna mayo)',     'food',        150, 0,  'A-1'),
('F003', 'ミックスサンド',      '混合三明治',         'Mixed sandwich',            'food',        320, 5,  'A-2'),
('F004', 'からあげ 5個入り',    '日式炸鸡（5块）',     'Fried chicken (5 pcs)',     'food',        280, 8,  'Counter'),
('F005', 'カップラーメン 醤油', '杯面（酱油味）',      'Cup noodles (soy sauce)',   'food',        230, 20, 'B-3'),
('D001', '緑茶 500ml',          '绿茶 500ml',         'Green tea 500ml',           'drink',       140, 30, 'C-1'),
('D002', 'ミネラルウォーター 500ml', '矿泉水 500ml',  'Mineral water 500ml',       'drink',       110, 0,  'C-1'),
('D003', 'ブラックコーヒー 缶', '黑咖啡（罐装）',      'Black coffee (can)',        'drink',       150, 15, 'C-2'),
('D004', 'オレンジジュース 1L', '橙汁 1L',            'Orange juice 1L',           'drink',       250, 4,  'C-2'),
('H001', 'ビニール傘',          '透明雨伞',           'Clear umbrella',            'daily',       700, 6,  'Entrance'),
('H002', '歯ブラシ',            '牙刷',               'Toothbrush',                'daily',       200, 10, 'D-1'),
('H003', 'マスク 7枚入り',      '口罩（7片装）',       'Face masks (7 pcs)',        'daily',       380, 0,  'D-1'),
('E001', 'モバイルバッテリー',  '充电宝',             'Portable battery charger',  'electronics', 2980, 3, 'E-1'),
('E002', 'USB-C ケーブル 1m',   'USB-C 数据线 1米',    'USB-C cable 1m',            'electronics', 1280, 7, 'E-1');
