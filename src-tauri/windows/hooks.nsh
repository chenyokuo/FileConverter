; Only this application's HKCU shell verbs. Do not touch associations.
!include "LogicLib.nsh"
!macro NSIS_HOOK_PREUNINSTALL
  SetRegView 64
  ReadRegStr $0 HKCU "Software\Classes\*\shell\FileConverter" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\*\shell\FileConverter" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\*\shell\FileConverter"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.aac\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.aac\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.aac\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.avi\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.avi\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.avi\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.avif\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.bmp\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.csv\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.csv\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.csv\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.doc\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.doc\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.doc\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.docx\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.docx\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.docx\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.eps\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.eps\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.eps\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.flac\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.flac\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.flac\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.gif\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.heic\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.html\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.html\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.html\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.jpg\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.jpg\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.jpg\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.md\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.md\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.md\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.mkv\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.mkv\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.mkv\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.mov\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.mov\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.mov\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.mp4\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.mp4\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.mp4\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.odp\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.odp\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.odp\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.ods\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.ods\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.ods\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.odt\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.odt\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.odt\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.ogg\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.ogg\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.ogg\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.opus\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.opus\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.opus\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.pdf\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.pdf\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.pdf\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.png\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.ppt\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.ppt\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.ppt\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.pptx\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.pptx\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.pptx\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.rtf\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.rtf\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.rtf\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.svg\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.svg\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.svg\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.tiff\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.tsv\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.tsv\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.tsv\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.txt\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.txt\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.txt\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.wav\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.wav\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.wav\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.webm\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.webm\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.webm\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToJPG" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToJPG" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToJPG"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.webp\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.wmv\shell\FileConverterToMP3" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.wmv\shell\FileConverterToMP3" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.wmv\shell\FileConverterToMP3"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.xls\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.xls\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.xls\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
  ReadRegStr $0 HKCU "Software\Classes\SystemFileAssociations\.xlsx\shell\FileConverterToPDF" "Owner"
  ${If} $0 == "studio.rai.converter"
    ReadRegStr $1 HKCU "Software\Classes\SystemFileAssociations\.xlsx\shell\FileConverterToPDF" "Executable"
    ${If} $1 == "$INSTDIR\FileConverter.exe"
      DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.xlsx\shell\FileConverterToPDF"
    ${EndIf}
  ${EndIf}
!macroend
