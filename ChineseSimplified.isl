; *** Inno Setup version 6.5.0+ Chinese Simplified messages ***
;
; To download user-contributed translations of this file, go to:
;   https://jrsoftware.org/files/istrans/
;
; Note: When translating this text, do not add periods (.) to the end of
; messages that didn't have them already, because on those messages Inno
; Setup adds the periods automatically (appending a period would result in
; two periods being displayed).
;
; Maintained by Zhenghan Yang
; Email: 847320916@QQ.com
; Translation based on network resource
; The latest Translation is on https://github.com/kira-96/Inno-Setup-Chinese-Simplified-Translation
;

[LangOptions]
; The following three entries are very important. Be sure to read and 
; understand the '[LangOptions] section' topic in the help file.
LanguageName=简体中文
; If Language Name display incorrect, uncomment next line
; LanguageName=<7B80><4F53><4E2D><6587>
; About LanguageID, to reference link:
; https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/a9eac961-e77d-41a6-90a5-ce1a8b0cdb9c
LanguageID=$0804
; About CodePage, to reference link:
; https://docs.microsoft.com/en-us/windows/win32/intl/code-page-identifiers
LanguageCodePage=936
; If the language you are translating to requires special font faces or
; sizes, uncomment any of the following entries and change them accordingly.
;DialogFontName=
;DialogFontSize=8
;WelcomeFontName=Verdana
;WelcomeFontSize=12
;TitleFontName=Arial
;TitleFontSize=29
;CopyrightFontName=Arial
;CopyrightFontSize=8

[Messages]

; *** 应用程序标题
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallAppFullTitle=%1 卸载

; *** Misc. common
InformationTitle=信息
ConfirmTitle=确认
ErrorTitle=错误

; *** SetupLdr messages
SetupLdrStartupMessage=现在将安装 %1。您想要继续吗？
LdrCannotCreateTemp=无法创建临时文件。安装程序已中止
LdrCannotExecTemp=无法执行临时目录中的文件。安装程序已中止
HelpTextNote=

; *** 启动错误消息
LastErrorMessage=%1。%n%n错误 %2: %3
SetupFileMissing=安装目录中缺少文件 %1。请修正这个问题或者获取程序的新副本。
SetupFileCorrupt=安装文件已损坏。请获取程序的新副本。
SetupFileCorruptOrWrongVer=安装文件已损坏，或是与这个安装程序的版本不兼容。请修正这个问题或获取新的程序副本。
InvalidParameter=无效的命令行参数：%n%n%1
SetupAlreadyRunning=安装程序正在运行。
WindowsVersionNotSupported=此程序不支持当前计算机运行的 Windows 版本。
WindowsServicePackRequired=此程序需要 %1 服务包 %2 或更高版本。
NotOnThisPlatform=此程序不能在 %1 上运行。
OnlyOnThisPlatform=此程序只能在 %1 上运行。
OnlyOnTheseArchitectures=此程序只能安装到为下列处理器架构设计的 Windows 版本中：%n%n%1
WinVersionTooLowError=此程序需要 %1 版本 %2 或更高。
WinVersionTooHighError=此程序不能安装于 %1 版本 %2 或更高。
AdminPrivilegesRequired=在安装此程序时您必须以管理员身份登录。
PowerUserPrivilegesRequired=在安装此程序时您必须以管理员身份或有权限的用户组身份登录。
SetupAppRunningError=安装程序发现 %1 当前正在运行。%n%n请先关闭正在运行的程序，然后点击"确定"继续，或点击"取消"退出。
UninstallAppRunningError=卸载程序发现 %1 当前正在运行。%n%n请先关闭正在运行的程序，然后点击"确定"继续，或点击"取消"退出。

; *** 启动问题
PrivilegesRequiredOverrideTitle=选择安装程序模式
PrivilegesRequiredOverrideInstruction=选择安装模式
PrivilegesRequiredOverrideText1=%1 可以为所有用户安装(需要管理员权限)，或仅为您安装。
PrivilegesRequiredOverrideText2=%1 可以仅为您安装，或为所有用户安装(需要管理员权限)。
PrivilegesRequiredOverrideAllUsers=为所有用户安装(&A)
PrivilegesRequiredOverrideAllUsersRecommended=为所有用户安装(&A) (建议选项)
PrivilegesRequiredOverrideCurrentUser=仅为我安装(&M)
PrivilegesRequiredOverrideCurrentUserRecommended=仅为我安装(&M) (建议选项)

; *** 其他错误
ErrorCreatingDir=安装程序无法创建目录"%1"
ErrorTooManyFilesInDir=无法在目录"%1"中创建文件，因为里面包含太多文件

; *** 安装程序公共消息
ExitSetupTitle=退出安装程序
ExitSetupMessage=安装程序尚未完成。如果现在退出，将不会安装该程序。%n%n您之后可以再次运行安装程序完成安装。%n%n现在退出安装程序吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装程序
AboutSetupMessage=%1 版本 %2%n%3%n%n%1 主页：%n%4
AboutSetupNote=
TranslatorNote=简体中文翻译由Kira(847320916@qq.com)维护。项目地址：https://github.com/kira-96/Inno-Setup-Chinese-Simplified-Translation

; *** 按钮
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&R)...
ButtonNewFolder=新建文件夹(&M)

; *** "选择语言"对话框消息
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=选择安装时使用的语言。

; *** 公共向导文字
ClickNext=点击"下一步"继续，或点击"取消"退出安装程序。
BeveledLabel=
BrowseDialogTitle=浏览文件夹
BrowseDialogLabel=在下面的列表中选择一个文件夹，然后点击"确定"。
NewFolderName=新建文件夹

; *** "欢迎"向导页
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=现在将安装 [name/ver] 到您的电脑中。%n%n建议您在继续安装前关闭所有其他应用程序。

; *** "密码"向导页
WizardPassword=密码
PasswordLabel1=这个安装程序有密码保护。
PasswordLabel3=请输入密码，然后点击"下一步"继续。密码区分大小写。
PasswordEditLabel=密码(&P)：
IncorrectPassword=您输入的密码不正确，请重新输入。

; *** "许可协议"向导页
WizardLicense=许可协议
LicenseLabel=请在继续安装前阅读以下重要信息。
LicenseLabel3=请仔细阅读下列许可协议。在继续安装前您必须同意这些协议条款。
LicenseAccepted=我同意此协议(&A)
LicenseNotAccepted=我不同意此协议(&D)

; *** "信息"向导页
WizardInfoBefore=信息
InfoBeforeLabel=请在继续安装前阅读以下重要信息。
InfoBeforeClickLabel=准备好继续安装后，点击"下一步"。
WizardInfoAfter=信息
InfoAfterLabel=请在继续安装前阅读以下重要信息。
InfoAfterClickLabel=准备好继续安装后，点击"下一步"。

; *** "用户信息"向导页
WizardUserInfo=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=用户名(&U)：
UserInfoOrg=组织(&O)：
UserInfoSerial=序列号(&S)：
UserInfoNameRequired=您必须输入用户名。

; *** "选择目标目录"向导页
WizardSelectDir=选择目标位置
SelectDirDesc=您想将 [name] 安装在哪里？
SelectDirLabel3=安装程序将安装 [name] 到下面的文件夹中。
SelectDirBrowseLabel=点击"下一步"继续。如果您想选择其他文件夹，点击"浏览"。
DiskSpaceGBLabel=至少需要有 [gb] GB 的可用磁盘空间。
DiskSpaceMBLabel=至少需要有 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=安装程序无法安装到一个网络驱动器。
CannotInstallToUNCPath=安装程序无法安装到一个 UNC 路径。
InvalidPath=您必须输入一个带驱动器卷标的完整路径，例如：%n%nC:\APP%n%n或UNC路径：%n%n\\server\share
InvalidDrive=您选定的驱动器或 UNC 共享不存在或不能访问。请选择其他位置。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 的可用空间才能安装，但选定驱动器只有 %2 KB 的可用空间。%n%n您一定要继续吗？
DirNameTooLong=文件夹名称或路径太长。
InvalidDirName=文件夹名称无效。
BadDirName32=文件夹名称不能包含下列任何字符：%n%n%1
DirExistsTitle=文件夹已存在
DirExists=文件夹：%n%n%1%n%n已经存在。您一定要安装到这个文件夹中吗？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹：%n%n%1%n%n不存在。您想要创建此文件夹吗？

; *** "选择组件"向导页
WizardSelectComponents=选择组件
SelectComponentsDesc=您想安装哪些程序组件？
SelectComponentsLabel2=选中您想安装的组件；取消您不想安装的组件。然后点击"下一步"继续。
FullInstallation=完全安装
; if possible don't translate 'Compact' as 'Minimal' (I mean 'Minimal' in your language)
CompactInstallation=简洁安装
CustomInstallation=自定义安装
NoUninstallWarningTitle=组件已存在
NoUninstallWarning=安装程序检测到下列组件已安装在您的电脑中：%n%n%1%n%n取消选中这些组件不会卸载它们。%n%n确定要继续吗？
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceGBLabel=当前选择的组件需要至少 [gb] GB 的磁盘空间。
ComponentsDiskSpaceMBLabel=当前选择的组件需要至少 [mb] MB 的磁盘空间。

; *** "选择附加任务"向导页
WizardSelectTasks=选择附加任务
SelectTasksDesc=您想要安装程序执行哪些附加任务？
SelectTasksLabel2=选择您想要安装程序在安装 [name] 时执行的附加任务，然后点击"下一步"。

; *** "选择开始菜单文件夹"向导页
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=安装程序应该在哪里放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在下列"开始"菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=点击"下一步"继续。如果您想选择其他文件夹，点击"浏览"。
MustEnterGroupName=您必须输入一个文件夹名。
GroupNameTooLong=文件夹名或路径太长。
InvalidGroupName=无效的文件夹名字。
BadGroupName=文件夹名不能包含下列任何字符：%n%n%1
NoProgramGroupCheck2=不创建开始菜单文件夹(&D)

; *** "准备安装"向导页
WizardReady=准备安装
ReadyLabel1=安装程序准备就绪，现在可以开始安装 [name] 到您的电脑。
ReadyLabel2a=点击"安装"继续此安装程序。如果您想重新考虑或修改任何设置，点击"上一步"。
ReadyLabel2b=点击"安装"继续此安装程序。
ReadyMemoUserInfo=用户信息：
ReadyMemoDir=目标位置：
ReadyMemoType=安装类型：
ReadyMemoComponents=已选择组件：
ReadyMemoGroup=开始菜单文件夹：
ReadyMemoTasks=附加任务：

; *** "正在安装"向导页
WizardInstalling=正在安装
InstallingLabel=安装程序正在安装 [name] 到您的电脑，请稍候。

; *** "安装完成"向导页
FinishedHeadingLabel=[name] 安装完成
FinishedLabelNoIcons=安装程序已在您的电脑中安装了 [name]。
FinishedLabel=安装程序已在您的电脑中安装了 [name]。您可以通过已安装的快捷方式运行此应用程序。
ClickFinish=点击"完成"退出安装程序。
FinishedRestartLabel=为完成 [name] 的安装，安装程序必须重新启动您的电脑。要立即重启吗？
FinishedRestartMessage=为完成 [name] 的安装，安装程序必须重新启动您的电脑。%n%n要立即重启吗？
ShowReadmeCheck=是，我想查阅自述文件
YesRadio=是，立即重启电脑(&Y)
NoRadio=否，稍后重启电脑(&N)
; used for example as 'Run MyProg.exe'
RunEntryExec=运行 %1
; used for example as 'View Readme.txt'
RunEntryShellExec=查阅 %1

[CustomMessages]

NameAndVersion=%1 版本 %2
AdditionalIcons=附加快捷方式：
CreateDesktopIcon=创建桌面快捷方式(&D)
CreateQuickLaunchIcon=创建快速启动栏快捷方式(&Q)
ProgramOnTheWeb=%1 网站
UninstallProgram=卸载 %1
LaunchProgram=运行 %1
AssocFileExtension=将 %2 文件扩展名与 %1 建立关联(&A)
AssocingFileExtension=正在将 %2 文件扩展名与 %1 建立关联...
AutoStartProgramGroupDescription=启动：
AutoStartProgram=自动启动 %1
AddonHostProgramNotFound=您选择的文件夹中无法找到 %1。%n%n您要继续吗？