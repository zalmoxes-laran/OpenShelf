# OpenShelf - Cultural Heritage 3D Assets Browser

**OpenShelf** is a modular Blender addon for browsing and importing 3D cultural heritage assets from online repositories.

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)
![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)

## 🚀 Features

- **🔍 Unified Search**: Single search interface across multiple cultural heritage repositories
- **📚 Multi-Repository Support**: Modular system supporting Ercolano (active) and future repositories
- **⚡ Smart Caching**: Intelligent download caching for improved performance
- **🎨 Integrated UI**: Clean panels directly in Blender's 3D viewport
- **🔧 Modular Architecture**: Easily extensible for new repositories and file formats
- **📊 Quality Assessment**: Asset quality scoring and validation
- **🏛️ Cultural Metadata**: Rich metadata preservation as custom properties

## 📦 Installation

### Prerequisites
- **Blender 4.2.0** or newer
- **Internet connection** for downloading assets
- **Python 3.10+** (included with Blender)

### Method 1: Download Release (Recommended)
1. Download the latest `.zip` release
2. In Blender: `Edit → Preferences → Add-ons → Install...`
3. Select the downloaded ZIP file
4. Enable "OpenShelf" in the add-ons list

### Method 2: Development Installation
```bash
git clone https://github.com/yourusername/openshelf.git
cd openshelf
# Copy to Blender addons directory or use development workflow below
```

## 🛠️ Development with VSCode

This project is optimized for development with **Visual Studio Code** and the **Blender Development** extension.

### Setup Development Environment

1. **Install VSCode Extensions**:
   - [Blender Development](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development)
   - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

2. **Clone Repository**:
   ```bash
   git clone https://github.com/yourusername/openshelf.git
   cd openshelf
   code .
   ```

3. **Configure Blender Path**:
   - Open VSCode settings (`Ctrl+,`)
   - Search for "Blender Development"
   - Set "Blender: Executable Path" to your Blender installation

4. **Launch Development**:
   - Press `Ctrl+Shift+P`
   - Type "Blender: Start" and select it
   - Choose "Start Development" option
   - Select the `openshelf` folder

5. **Hot Reload**:
   - Press `Ctrl+Shift+P` → "Blender: Reload Addons"
   - Or use `F5` if configured

### VSCode Configuration

The project includes a `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug OpenShelf in Blender",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/__init__.py",
            "console": "integratedTerminal",
            "blender": {
                "executable": "blender",
                "args": ["--python-console"]
            }
        }
    ]
}
```

## 🎯 Usage

### Basic Workflow

1. **Open Blender** and find the "OpenShelf" tab in the 3D viewport sidebar (`N` key)

2. **Select Repository**: Choose "Ercolano" or "All Repositories"

3. **Search Assets**:
   - Enter search terms in the main search box
   - Apply filters for object type, material, chronology
   - Click "Search" to find assets

4. **Import Assets**:
   - Browse search results
   - Click "Import" on desired assets
   - Objects are imported with cultural metadata

### Advanced Features

#### Search Filters
- **Object Type**: `anello`, `vaso`, `coppa`, `lucerna`, etc.
- **Material**: `oro`, `argilla`, `bronzo`, `marmo`, etc.
- **Chronology**: `sec. I d.C.`, `età imperiale`, etc.
- **Inventory Number**: Specific museum inventory numbers

#### Quick Search Buttons
- **Rings**: Search for ancient rings
- **Vases**: Search for pottery and ceramics  
- **Gold**: Search for gold objects
- **1st Century**: Search by historical period

#### Import Options
- **Scale**: Adjust import scale (1-1000%)
- **Auto Center**: Center objects at origin
- **Materials**: Apply materials automatically
- **Metadata**: Add cultural heritage metadata

### Cultural Metadata

Imported objects include rich metadata as custom properties:
```python
obj["openshelf_id"]              # Unique asset ID
obj["openshelf_name"]            # Display name
obj["openshelf_repository"]      # Source repository
obj["openshelf_object_type"]     # Type of cultural object
obj["openshelf_materials"]       # Materials used
obj["openshelf_chronology"]      # Historical period
obj["openshelf_inventory_number"] # Museum inventory
obj["openshelf_quality_score"]   # Quality assessment
obj["openshelf_license"]         # Usage license
```

## 🏗️ Architecture

OpenShelf uses a clean, modular architecture:

```
openshelf/
├── blender_manifest.toml           # Blender 4.2+ extension manifest
├── __init__.py                     # Entry point
├── operators/                      # Blender operators
│   ├── search_operators.py         # Search and filtering
│   ├── import_operators.py         # Asset import
│   └── repository_operators.py     # Repository management
├── ui/                            # User interface
│   ├── search_panel.py            # Main search interface
│   ├── viewport_panels.py         # Additional viewport panels
│   └── preferences_panel.py       # Addon preferences
├── utils/                         # Reusable utilities
│   ├── download_manager.py        # Download and caching
│   ├── obj_loader.py              # OBJ file import
│   ├── gltf_loader.py             # GLTF/GLB import
│   └── file_utils.py              # File operations
├── repositories/                  # Repository system
│   ├── base_repository.py         # Base repository class
│   ├── ercolano_repository.py     # Ercolano implementation
│   └── registry.py                # Repository registry
├── properties/                    # Blender properties
│   └── scene_properties.py        # Scene-level properties
└── data/                         # Static data
    ├── repository_configs.json    # Repository configurations
    └── icons/                     # Custom icons
```

### Key Components

#### Repository System
- **BaseRepository**: Abstract base class for all repositories
- **ErcolanoRepository**: Implementation for Ercolano museum data
- **RepositoryRegistry**: Centralized repository management

#### Loader System
- **OBJLoader**: Reusable OBJ file import with cultural metadata
- **GLTFLoader**: GLTF/GLB import support (future-ready)
- **Modular Design**: Easy to add new 3D formats

#### UI Components
- **Search Panel**: Main search interface with filters
- **Results Panel**: Display and interact with search results
- **Import Panel**: Import settings and progress
- **Object Info Panel**: Display cultural metadata for selected objects

## 🌍 Supported Repositories

### ✅ Active Repositories

#### Ercolano (Museo Archeologico Virtuale di Ercolano)
- **Assets**: ~2,100 archaeological artifacts
- **Formats**: OBJ with textures
- **Content**: Roman-era artifacts from Herculaneum
- **License**: Public institution (terms vary)
- **Quality**: High-quality museum digitization

### 🔮 Planned Repositories

#### Pompei (Parco Archeologico di Pompei)
- **Status**: Planned
- **Assets**: Archaeological artifacts from Pompeii
- **Formats**: OBJ, GLTF

#### Europeana
- **Status**: Planned  
- **Assets**: 1M+ European cultural heritage items
- **Formats**: Various

#### Smithsonian Institution
- **Status**: Planned
- **Assets**: 500+ museum objects
- **Formats**: OBJ, GLTF, USDZ

## 🔧 Configuration

### Repository Configuration

Edit `data/repository_configs.json` to modify repository settings:

```json
{
  "repositories": {
    "ercolano": {
      "name": "Ercolano",
      "api_url": "https://mude.cultura.gov.it/searchInv/iv/json/lista",
      "supported_formats": ["obj"],
      "cache_duration_hours": 24
    }
  }
}
```

### Addon Preferences

Access via `Edit → Preferences → Add-ons → OpenShelf`:

- **Repository Settings**: Default repository, timeouts
- **Import Settings**: Scale, centering, materials
- **Cache Settings**: Size limits, expiry times
- **UI Settings**: Results limits, compact mode
- **Advanced**: Debug mode, logging levels

## 🤝 Contributing

### Adding New Repositories

1. **Create Repository Class**:
   ```python
   # repositories/my_repository.py
   class MyRepository(BaseRepository):
       def fetch_assets(self, limit=100):
           # Implement data fetching
           pass
       
       def parse_raw_data(self, raw_data):
           # Convert to CulturalAsset objects
           pass
   ```

2. **Register Repository**:
   ```python
   # repositories/__init__.py
   from .my_repository import MyRepository
   
   def register():
       RepositoryRegistry.register_repository(MyRepository())
   ```

### Adding New 3D Formats

1. **Create Loader**:
   ```python
   # utils/my_format_loader.py
   class MyFormatLoader:
       @staticmethod
       def import_my_format(filepath, **kwargs):
           # Implement format import
           pass
   ```

2. **Integrate in Import Operators**:
   ```python
   # operators/import_operators.py
   elif file_ext == '.myformat':
       imported_obj = MyFormatLoader.import_my_format(model_path)
   ```

### Development Guidelines

- **Code Style**: Follow PEP 8
- **Documentation**: Document all public methods
- **Testing**: Test with real repository data
- **Error Handling**: Graceful error handling and user feedback
- **Compatibility**: Maintain Blender 4.2+ compatibility

## 📝 Roadmap

### Version 1.1 (Next Release)
- [ ] Thumbnail preview support
- [ ] Download progress indicators
- [ ] Advanced search filters
- [ ] Material auto-assignment improvements

### Version 1.2 (Future)
- [ ] GLTF/GLB support completion
- [ ] Pompei repository integration
- [ ] Batch import improvements
- [ ] Search result favorites

### Version 2.0 (Long-term)
- [ ] AI-powered semantic search
- [ ] 3D preview in interface
- [ ] Extended Matrix (EM) integration
- [ ] Web interface companion

## 🛡️ Security & Privacy

- **Network Security**: SSL certificate verification (configurable)
- **Data Privacy**: No personal data collection
- **Local Caching**: All cached data stored locally
- **Permissions**: Network and file access only (declared in manifest)

## 🐛 Troubleshooting

### Common Issues

**"No assets found"**
- Check internet connection
- Verify repository is online: Use "Test" button
- Try different search terms
- Clear cache and retry

**"Import failed"**
- Check file format support
- Verify sufficient disk space
- Review console for detailed errors
- Try different asset

**"Repository connection failed"**
- Check firewall settings
- Verify repository URL in preferences
- Test with different repository
- Enable debug mode for detailed logs

### Debug Mode

Enable in `Preferences → OpenShelf → Advanced → Debug Mode`:
- Detailed console logging
- Network request debugging
- File operation tracking
- Performance metrics

### Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/openshelf/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/openshelf/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/openshelf/wiki)

## 📄 License

**GPL-3.0-or-later** - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Museo Archeologico Virtuale di Ercolano** for open data access
- **Blender Foundation** for the excellent development platform
- **ICCD (Istituto Centrale per il Catalogo e la Documentazione)** for cultural heritage standards
- **Cultural heritage community** for inspiration and feedback

## 📞 Contact

- **Author**: Your Name
- **Email**: your.email@example.com
- **Website**: https://your-website.com
- **Repository**: https://github.com/yourusername/openshelf

---

*Developed with ❤️ for the cultural heritage community*

**Made possible by open data initiatives and cultural institutions worldwide**
