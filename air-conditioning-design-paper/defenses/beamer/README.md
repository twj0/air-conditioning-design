# Beamer 答辩汇报

本目录用于存放基于 `college-beamer` 模板生成的课程设计答辩幻灯片。

## 当前主文件

- `college-beamer/air_conditioning_design_defense.tex`

## 编译方式

在 `college-beamer/` 目录下执行：

```powershell
latexmk -pdf air_conditioning_design_defense.tex
```

由于当前幻灯片使用了 `zh` 选项，`.latexmkrc` 会自动选择 `XeLaTeX`。

## 输出位置

- `college-beamer/build/air_conditioning_design_defense.pdf`

## 内容说明

当前版本面向 `8` 到 `10` 分钟课程设计答辩，整体约 `20` 页，复用了论文中的建筑模型图和结果图，主题为：

- 五个城市
- 统一办公建筑母版
- `Ideal Loads`
- `VRF+DOAS`
- `FCU+DOAS`
- 适宜性评价
