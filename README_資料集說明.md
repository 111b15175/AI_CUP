# 太陽能板異常偵測資料集說明（補充）

本文件與 `train_groups.csv` 原應隨資料集一併提供，現補發。提交格式與評分方式請以官方 evaluation kit（author-kit_1012）的 README.md 為準。

## 目錄結構

解壓縮後的資料夾名稱不影響使用。提交檔的 key 為 `test/` 開頭的相對路徑，必須與 kit 內 `test_images.csv` 的字串完全一致，例如 `test/EO/image/test_001.jpg`。

```
train/EO/image/*.jpg    train/EO/label/*.json    可見光（EO）訓練影像與標註
train/IR/image/*.jpg    train/IR/label/*.json    紅外（IR）訓練影像與標註
test/EO/image/*.jpg                              可見光測試影像（無標註）
test/IR/image/*.jpg                              紅外測試影像（無標註）
```

測試影像的完整清單見 kit 內的 `test_images.csv`。

與競賽規則頁用語的對應：規則頁所稱的 RGB 即本資料集的 EO；annotations/ 即各模態的 `label/`。規則頁提到的場景編號不另外提供；訓練集的分組資訊見 `train_groups.csv`。

## 影像配對

EO 與 IR 使用相同檔名，同名者為同一時刻拍攝的可見光／紅外配對影像。train 與 test 的每個檔名都同時存在於 EO 和 IR。兩種模態的解析度與視角不同，標註各自使用該影像的座標系統，不保證像素對齊。

## 類別

| 類別 | 說明 |
|---|---|
| `solar_panel` | 太陽能模組（正常） |
| `hotspot` | 熱斑異常，只出現在 IR 影像 |
| `crack` | 裂紋異常，只出現在 EO 影像 |

異常以整個模組為範圍標註，同一個模組原則上只標一個類別。

## 標註格式

訓練標註為 labelme JSON。`shapes` 內每個物件含 `label`、`points`、`shape_type`（一律為 `"polygon"`）與 `reason`。`reason` 是異常成因的文字描述，`solar_panel` 為 `null`。

## 影像說明

影像已做去識別化處理：標註框以外的區域一律填黑。這是資料集的既定形式，train 與 test 一致。

## 分組資訊（train_groups.csv）

`train_groups.csv` 有兩欄：`frame_id`（訓練影像的檔名，不含副檔名）與 `group`（分組代號）。group 相同的影格來自同一次連續拍攝，畫面高度相似。自行切分驗證集時，請以 group 為單位，否則近乎重複的影像會讓驗證分數偏高。test 不提供分組資訊。

## 檔名

檔名為匿名編號，不含任何時間或來源資訊。
